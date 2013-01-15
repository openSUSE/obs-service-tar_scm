#!/usr/bin/python

from   githgtests  import GitHgTests
from   hgfixtures  import HgFixtures
from   utils       import run_hg

class HgTests(GitHgTests):
    scm = 'hg'
    initial_clone_command = 'hg clone'
    update_cache_command  = 'hg pull'
    fixtures_class = HgFixtures

    abbrev_hash_format = '{node|short}'
    timestamp_format   = '{date}'
    yyyymmdd_format    = '{date|shortdate}'

    def default_version(self):
        return self.rev(2)
