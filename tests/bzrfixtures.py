#!/usr/bin/env python

from typing import Any
import os

from tests.fixtures import Fixtures
from tests.utils    import run_bzr


class BzrFixtures(Fixtures):
    """Methods to create and populate a bzr repository.

    bzr tests use this class in order to have something to test against.
    """

    def init(self) -> Any:
        self.create_repo()
        self.create_commits(2)

    def run(self, cmd: Any) -> Any:
        return run_bzr(self.repo_path, cmd)

    def create_repo(self) -> Any:
        os.makedirs(self.repo_path)
        os.chdir(self.repo_path)
        self.safe_run('init')
        self.safe_run('whoami "%s"' % self.name_and_email)
        self.wdir = self.repo_path
        print("created repo %s" % self.repo_path)

    def record_rev(self, *args: Any) -> Any:
        rev_num = args[0]
        self.revs[rev_num] = str(rev_num)
        self.scmlogs.annotate("Recorded rev %d" % rev_num)

    def get_committer_date(self) -> Any:
        '''There seems to be no way to create a commit with a given timestamp
        set for Bazar.'''
        return ''
