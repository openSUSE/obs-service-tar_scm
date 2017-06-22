import hashlib
import sys
import re
import dateutil.parser
import os
import logging
from TarSCM.scm.base import Scm


class svn(Scm):
    def fetch_upstream_scm(self):
        """SCM specific version of fetch_uptream for svn."""
        command = ['svn', 'checkout', '--non-interactive', self.url,
                   self.clone_dir]
        if self.revision:
            command.insert(4, '-r%s' % self.revision)
        if not self.is_sslverify_enabled():
            command.insert(3, '--trust-server-cert')

        wd = os.path.abspath(os.path.join(self.clone_dir, os.pardir))

        self.helpers.safe_run(command, wd, interactive=sys.stdout.isatty())

    def update_cache(self):
        """Update sources via svn."""
        command = ['svn', 'update']
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

        svn_info = self.helpers.safe_run(['svn', 'info'], self.clone_dir)[1]

        version = ''
        match = re.search('Last Changed Rev: (.*)', svn_info, re.MULTILINE)
        if match:
            version = match.group(1).strip()
        return re.sub('%r', version, versionformat)

    def get_timestamp(self):
        svn_info = self.helpers.safe_run(['svn', 'info', '-rHEAD'],
                                         self.clone_dir)[1]

        match = re.search('Last Changed Date: (.*)', svn_info, re.MULTILINE)
        if not match:
            return 0

        timestamp = match.group(1).strip()
        timestamp = re.sub('\(.*\)', '', timestamp)
        timestamp = dateutil.parser.parse(timestamp).strftime("%s")
        return int(timestamp)

    def detect_changes_scm(self, subdir, changes):
        """Detect changes between SVN revisions."""
        last_rev = changes['revision']
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
            return

        if not first_run:
            # Increase last_rev by 1 so we dont get duplication of log messages
            last_rev = int(last_rev) + 1

        logging.debug("Generating changes between %s and %s", last_rev,
                      current_rev)
        lines = self._get_log(clone_dir, last_rev, current_rev)

        changes['revision'] = current_rev
        changes['lines'] = lines
        return changes

    def get_repocache_hash(self, subdir):
        """Calculate hash fingerprint for repository cache."""
        return hashlib.sha256(self.url + '/' + subdir).hexdigest()

    def _get_log(self, clone_dir, revision1, revision2):
        new_lines = []

        xml_lines = self.helpers.safe_run(
            ['svn', 'log', '-r%s:%s' % (revision1, revision2), '--xml'],
            clone_dir
        )[1]

        lines = re.findall(r"<msg>.*?</msg>", xml_lines, re.S)

        for line in lines:
            line = line.replace("<msg>", "").replace("</msg>", "")
            new_lines = new_lines + line.split("\n")

        return new_lines

    def _get_rev(self, clone_dir, num_commits):
        revisions = self.helpers.safe_run(
            ['svn', 'log', '-l%d' % num_commits, '-q',
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
