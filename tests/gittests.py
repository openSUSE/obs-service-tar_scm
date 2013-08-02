#!/usr/bin/python

import datetime

from   githgtests  import GitHgTests
from   gitfixtures import GitFixtures
from   utils       import run_git

class GitTests(GitHgTests):
    scm = 'git'
    initial_clone_command = 'git clone'
    update_cache_command  = 'git fetch'
    fixtures_class = GitFixtures

    abbrev_hash_format = '%h'
    timestamp_format   = '%ct'
    yyyymmdd_format    = '%cd'

    def default_version(self):
        return self.timestamps(self.rev(2))

    def version(self, rev):
        # Hyphens aren't allowed in version number.  This substitution
        # mirrors the use of sed "s@-@@g" in tar_scm.
        return self.timestamps(self.rev(rev)).replace('-', '')

    # This comment line helps align lines with hgtests.py.
    def dateYYYYMMDD(self, rev):
        dateobj = datetime.date.fromtimestamp(float(self.timestamps(rev)))
        return dateobj.strftime("%4Y%02m%02d")

    def test_versionformat_parenttag(self):
        self.tar_scm_std('--versionformat', "@PARENT_TAG@")
        self.assertTarOnly(self.basename(version = self.rev(2)))
