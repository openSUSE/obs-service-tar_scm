import sys
import re
import dateutil.parser
from base import scm

class bzr(scm):
    def fetch_upstream_scm(self, clone_dir, kwargs):
        """SCM specific version of fetch_uptream for bzr."""
        command = ['bzr', 'checkout', self.url, clone_dir]
        if self.revision:
            command.insert(3, '-r')
            command.insert(4, self.revision)
        if not self.is_sslverify_enabled(kwargs):
            command.insert(2, '-Ossl.cert_reqs=None')
        self.helpers.safe_run(command, self.repodir, interactive=sys.stdout.isatty())

    def update_cache(self, clone_dir):
        """Update sources via bzr."""
        command = ['bzr', 'update']
        if self.revision:
            command.insert(3, '-r')
            command.insert(4, self.revision)
        self.helpers.safe_run(command, cwd=clone_dir, interactive=sys.stdout.isatty())

    def detect_version(self, args, repodir):
        """Automatic detection of version number for checked-out BZR repository."""
        versionformat = args['versionformat']
        if versionformat is None:
            versionformat = '%r'

        version = self.helpers.safe_run(['bzr', 'revno'], repodir)[1]
        return re.sub('%r', version.strip(), versionformat)

    def get_timestamp(self, args, repodir):
        log = self.helpers.safe_run(['bzr', 'log', '--limit=1', '--log-format=long'],
                       repodir)[1]
        match = re.search(r'timestamp:(.*)', log, re.MULTILINE)
        if not match:
            return 0
        timestamp = dateutil.parser.parse(match.group(1).strip()).strftime("%s")
        return int(timestamp)
