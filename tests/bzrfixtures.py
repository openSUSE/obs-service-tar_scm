#!/usr/bin/python

import os

from   fixtures  import Fixtures
from   utils     import mkfreshdir, run_bzr

class BzrFixtures(Fixtures):
    def init(self):
        self.create_repo()
        self.create_commits(2)

    def run(self, cmd):
        return run_bzr(self.repo_path, cmd)

    def create_repo(self):
        os.makedirs(self.repo_path)
        os.chdir(self.repo_path)
        self.run('init')
        self.run('whoami "%s"' % self.name_and_email)
        self.wd = self.repo_path
        print "created repo", self.repo_path

    def record_rev(self, wd, rev_num):
        self.revs[rev_num] = str(rev_num)
        self.scmlogs.annotate("Recorded rev %d" % rev_num)
