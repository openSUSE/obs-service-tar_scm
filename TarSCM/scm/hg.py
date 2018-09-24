import sys
import re
import os
import tempfile
import shutil
import logging
from TarSCM.scm.base import Scm


class Hg(Scm):
    scm = 'hg'

    hgtmpdir = tempfile.mkdtemp()

    def _get_scm_cmd(self):
        """Compose a HG-specific command line using http proxies."""
        # Mercurial requires declaring proxies via a --config parameter
        scmcmd = ['hg']
        if self.httpproxy:
                logging.debug("using " + self.hgtmpdir)
                f = open(self.hgtmpdir + "/tempsettings.rc", "wb")
                f.write('[http_proxy]\n')

                regexp_proxy = re.match('http://(.*):(.*)',
                                        self.httpproxy,
                                        re.M | re.I)

                if regexp_proxy.group(1) is not None:
                        print ('using proxy host: ' + regexp_proxy.group(1))
                        f.write('host=' + regexp_proxy.group(1))
                if regexp_proxy.group(2) is not None:
                        print ('using proxy port: ' + regexp_proxy.group(2))
                        f.write('port=' + regexp_proxy.group(2))
                if self.noproxy is not None:
                        print ('using proxy exceptions: ' +
                               self.noproxy)
                        f.write('no=' + self.noproxy)
                f.close()

                # we just point Mercurial to where the config file is
                os.environ['HGRCPATH'] = self.hgtmpdir

        return scmcmd

    def switch_revision(self):
        """Switch sources to revision."""
        if self.revision is None:
            self.revision = 'tip'

        rcode, _ = self.helpers.run_cmd(self._get_scm_cmd() +
                                        ['update', self.revision],
                                        cwd=self.clone_dir,
                                        interactive=sys.stdout.isatty())
        if rcode:
            sys.exit('%s: No such revision' % self.revision)

    def fetch_upstream_scm(self):
        """SCM specific version of fetch_uptream for hg."""
        command = self._get_scm_cmd() + ['clone', self.url, self.clone_dir]
        if not self.is_sslverify_enabled():
            command += ['--insecure']
        wdir = os.path.abspath(os.path.join(self.clone_dir, os.pardir))
        self.helpers.safe_run(command, wdir,
                              interactive=sys.stdout.isatty())

    def update_cache(self):
        """Update sources via hg."""
        try:
            self.helpers.safe_run(self._get_scm_cmd() +
                                  ['pull'], cwd=self.clone_dir,
                                  interactive=sys.stdout.isatty())
        except SystemExit as exc:
            # Contrary to the docs, hg pull returns exit code 1 when
            # there are no changes to pull, but we don't want to treat
            # this as an error.
            if re.match('.*no changes found.*', str(exc)) is None:
                raise

    def detect_version(self, args):
        """
        Automatic detection of version number for checked-out HG repository.
        """
        versionformat = args['versionformat']
        if versionformat is None:
            versionformat = '{rev}'

        version = self.helpers.safe_run(self._get_scm_cmd() +
                                        ['id', '-n'], self.clone_dir)[1]

        # Mercurial internally stores commit dates in its changelog
        # context objects as (epoch_secs, tz_delta_to_utc) tuples (see
        # mercurial/util.py).  For example, if the commit was created
        # whilst the timezone was BST (+0100) then tz_delta_to_utc is
        # -3600.  In this case,
        #
        #     hg log -l1 -r$rev --template '{date}\n'
        #
        # will result in something like '1375437706.0-3600' where the
        # first number is timezone-agnostic.  However, hyphens are not
        # permitted in rpm version numbers, so tar_scm removes them via
        # sed.  This is required for this template format for any time
        # zone "numerically east" of UTC.
        #
        # N.B. since the extraction of the timestamp as a version number
        # is generally done in order to provide chronological sorting,
        # ideally we would ditch the second number.  However the
        # template format string is left up to the author of the
        # _service file, so we can't do it here because we don't know
        # what it will expand to.  Mercurial provides template filters
        # for dates (e.g. 'hgdate') which _service authors could
        # potentially use, but unfortunately none of them can easily
        # extract only the first value from the tuple, except for maybe
        # 'sub(...)' which is only available since 2.4 (first introduced
        # in openSUSE 12.3).

        version = self.helpers.safe_run(
            self._get_scm_cmd() +
            [
                'log',
                '-l1',
                "-r%s" % version.strip(),
                '--template',
                versionformat
            ],
            self.clone_dir
        )[1]
        return self.version_iso_cleanup(version)

    def get_timestamp(self):
        data = {"parent_tag": None, "versionformat": "{date}"}
        timestamp = self.detect_version(data)
        timestamp = re.sub(r'([0-9]+)\..*', r'\1', timestamp)
        return int(timestamp)

    def cleanup(self):
        try:
                shutil.rmtree(self.hgtmpdir, ignore_errors=True)
        except:
                logging.debug("error on cleanup:", sys.exc_info()[0])
                raise

    def check_url(self):
        """check if url is a remote url"""
        if not re.match("^https?://", self.url):
            return False
        return True
