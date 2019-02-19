import sys
import re
import os
import dateutil.parser
from TarSCM.scm.base import Scm


class Bzr(Scm):
    scm = 'bzr'

    def _get_scm_cmd(self):
        """Compose a BZR-specific command line using http proxies."""
        # Bazaar honors the http[s]_proxy variables, no action needed
        return [self.scm]

    def fetch_upstream_scm(self):
        """SCM specific version of fetch_uptream for bzr."""
        command = self._get_scm_cmd() + ['checkout', self.url, self.clone_dir]
        if self.revision:
            command.insert(3, '-r')
            command.insert(4, self.revision)
        if not self.is_sslverify_enabled():
            command.insert(2, '-Ossl.cert_reqs=None')
        wdir = os.path.abspath(os.path.join(self.clone_dir, os.pardir))
        self.helpers.safe_run(command, wdir, interactive=sys.stdout.isatty())

    def update_cache(self):
        """Update sources via bzr."""
        command = self._get_scm_cmd() + ['update']
        if self.revision:
            command.insert(3, '-r')
            command.insert(4, self.revision)
        self.helpers.safe_run(
            command,
            cwd=self.clone_dir,
            interactive=sys.stdout.isatty()
        )

    def detect_version(self, args):
        """
        Automatic detection of version number for checked-out BZR repository.
        """
        versionformat = args['versionformat']
        if versionformat is None:
            versionformat = '%r'

        version = self.helpers.safe_run(self._get_scm_cmd() + ['revno'],
                                        self.clone_dir)[1]
        return re.sub('%r', version.strip().decode(), versionformat)

    def get_timestamp(self):
        log = self.helpers.safe_run(
            self._get_scm_cmd() + ['log', '--limit=1', '--log-format=long'],
            self.clone_dir
        )[1]
        match = re.search(r'timestamp:(.*)', log.decode(), re.MULTILINE)
        if not match:
            return 0
        tsm = match.group(1).strip()
        timestamp = dateutil.parser.parse(tsm).strftime("%s")
        return int(timestamp)

    # no cleanup is necessary for bzr
    def cleanup(self):
        pass

    def check_url(self):
        """check if url is a remote url"""
        if not re.match("^((a?ftp|bzr|https?)://|lp:)", self.url):
            return False
        return True
