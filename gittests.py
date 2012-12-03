#!/usr/bin/python

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

    def default_version(self):
        return self.timestamps(self.rev(2))
