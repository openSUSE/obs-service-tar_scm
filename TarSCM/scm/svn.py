import hashlib
import sys
import re
import os
import logging
import tempfile
import shutil

import dateutil.parser

from TarSCM.scm.base import Scm


class Svn(Scm):
    scm = 'svn'

    Scm.__init__
    svntmpdir = tempfile.mkdtemp()

    def _get_scm_cmd(self):
        """Compose a SVN-specific command line using http proxies."""
        # Subversion requires declaring proxies in a file, as it does not
        # support the http[s]_proxy variables. This creates the temporary
        # config directory that will be added via '--config-dir'
        scmcmd = ['svn']
        if self.httpproxy:
                logging.debug("using " + self.svntmpdir)
                f = open(self.svntmpdir + "/servers", "wb")
                f.write('[global]\n')

                regexp_proxy = re.match('http://(.*):(.*)',
                                        self.httpproxy,
                                        re.M | re.I)

                if regexp_proxy.group(1) is not None:
                        logging.debug('using proxy host: ' +
                                      regexp_proxy.group(1))
                        f.write('http-proxy-host=' +
                                regexp_proxy.group(1) + '\n')

                if regexp_proxy.group(2) is not None:
                        logging.debug('using proxy port: ' +
                                      regexp_proxy.group(2))
                        f.write('http-proxy-port=' +
                                regexp_proxy.group(2) + '\n')

                if self.noproxy is not None:
                        logging.debug('using proxy exceptions: ' +
                                      self.noproxy)
                        no_proxy_domains = []
                        no_proxy_domains.append(tuple(self.noproxy.split(",")))
                        no_proxy_string = ""

                # for some odd reason subversion expects the domains
                # to have an asterisk
                for i in range(len(no_proxy_domains[0])):
                        tmpstr = str(no_proxy_domains[0][i]).strip()
                        if tmpstr.startswith('.'):
                                no_proxy_string += '*' + tmpstr
                        else:
                                no_proxy_string += tmpstr

                        if i < len(no_proxy_domains[0]) - 1:
                                no_proxy_string += ','

                no_proxy_string += '\n'
                logging.debug('no_proxy string = ' + no_proxy_string)
                f.write('http-proxy-exceptions=' + no_proxy_string)
                f.close()
                scmcmd += ['--config-dir', self.svntmpdir]

        return scmcmd

    def fetch_upstream_scm(self):
        """SCM specific version of fetch_uptream for svn."""
        command = self._get_scm_cmd() + ['checkout', '--non-interactive',
                                         self.url, self.clone_dir]
        if self.revision:
            command.insert(4, '-r%s' % self.revision)
        if not self.is_sslverify_enabled():
            command.insert(3, '--trust-server-cert')

        wdir = os.path.abspath(os.path.join(self.clone_dir, os.pardir))

        self.helpers.safe_run(command, wdir, interactive=sys.stdout.isatty())

    def update_cache(self):
        """Update sources via svn."""
        command = self._get_scm_cmd() + ['update']
        if self.revision:
            command.insert(3, "-r%s" % self.revision)
        self.helpers.safe_run(command, cwd=self.clone_dir,
                              interactive=sys.stdout.isatty())

    def detect_version(self, args):
        """
        Automatic detection of version number for checked-out SVN repository.
        """
        versionformat = args['versionformat']
        if versionformat is None:
            versionformat = '%r'

        svn_info = self.helpers.safe_run(self._get_scm_cmd() + ['info'],
                                         self.clone_dir)[1]

        version = ''
        match = re.search('Last Changed Rev: (.*)', svn_info, re.MULTILINE)
        if match:
            version = match.group(1).strip()
        return re.sub('%r', version, versionformat)

    def get_timestamp(self):
        svn_info = self.helpers.safe_run(self._get_scm_cmd() + ['info',
                                                                '-rHEAD'],
                                         self.clone_dir)[1]

        match = re.search('Last Changed Date: (.*)', svn_info, re.MULTILINE)
        if not match:
            return 0

        timestamp = match.group(1).strip()
        timestamp = re.sub(r'\(.*\)', '', timestamp)
        timestamp = dateutil.parser.parse(timestamp).strftime("%s")
        return int(timestamp)

    def detect_changes_scm(self, subdir, chgs):
        """Detect changes between SVN revisions."""
        last_rev = chgs['revision']
        first_run = False
        if subdir:
            clone_dir = os.path.join(self.clone_dir, subdir)
        else:
            clone_dir = self.clone_dir

        if last_rev is None:
            last_rev = self._get_rev(clone_dir, 10)
            logging.debug("First run get log for initial release")
            first_run = True

        current_rev = self._get_rev(clone_dir, 1)

        if last_rev == current_rev:
            logging.debug("No new commits, skipping changes file generation")
            return None

        if not first_run:
            # Increase last_rev by 1 so we dont get duplication of log messages
            last_rev = int(last_rev) + 1

        logging.debug("Generating changes between %s and %s", last_rev,
                      current_rev)
        lines = self._get_log(clone_dir, last_rev, current_rev)

        chgs['revision'] = current_rev
        chgs['lines'] = lines
        return chgs

    def get_repocache_hash(self, subdir):
        """Calculate hash fingerprint for repository cache."""
        return hashlib.sha256(self.url + '/' + subdir).hexdigest()

    def _get_log(self, clone_dir, revision1, revision2):
        new_lines = []

        xml_lines = self.helpers.safe_run(
            self._get_scm_cmd() + ['log', '-r%s:%s' % (revision2, revision1),
                                   '--xml'],
            clone_dir
        )[1]

        lines = re.findall(r"<msg>.*?</msg>", xml_lines, re.S)

        for line in lines:
            line = line.replace("<msg>", "").replace("</msg>", "")
            new_lines = new_lines + line.split("\n")

        return new_lines

    def _get_rev(self, clone_dir, num_commits):
        revisions = self.helpers.safe_run(
            self._get_scm_cmd() + ['log', '-l%d' % num_commits, '-q',
                                   '--incremental'], cwd=clone_dir
        )[1].split('\n')
        # remove blank entry on end
        revisions.pop()
        # return last entry
        revision = revisions[-1]
        # retrieve the revision number and remove r
        revision = re.search(r'^r[0-9]*', revision, re.M).group().replace("r",
                                                                          "")
        return revision

    def cleanup(self):
        try:
                shutil.rmtree(self.svntmpdir, ignore_errors=True)
        except:
                logging.debug("error on cleanup:", sys.exc_info()[0])
                raise
