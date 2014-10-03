#!/usr/bin/python

import os

from fixtures import Fixtures
from utils    import mkfreshdir, quietrun, run_svn


class SvnFixtures(Fixtures):

    """Methods to create and populate a svn repository.

    svn tests use this class in order to have something to test against.
    """

    def init(self):
        self.wd_path = self.container_dir + '/wd'

        self.create_repo()
        self.checkout_repo()

        self.added = {}

        self.create_commits(2)

    def run(self, cmd):
        return run_svn(self.wd_path, cmd)

    def create_repo(self):
        quietrun('svnadmin create ' + self.repo_path)
        print "created repo", self.repo_path

    def checkout_repo(self):
        mkfreshdir(self.wd_path)
        quietrun('svn checkout %s %s' % (self.repo_url, self.wd_path))
        self.wd = self.wd_path

    def do_commit(self, wd, new_rev, newly_created):
        for new in newly_created:
            if new not in self.added:
                self.safe_run('add ' + new)
                self.added[new] = True
        self.safe_run('commit -m%d' % new_rev)
        return new_rev

    def get_metadata(self, formatstr):
        return self.safe_run('log -n1' % formatstr)[0]

    def record_rev(self, wd, rev_num):
        self.revs[rev_num] = str(rev_num)
        self.scmlogs.annotate("Recorded rev %d" % rev_num)
