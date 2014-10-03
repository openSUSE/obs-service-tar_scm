#!/usr/bin/python

import os

from fixtures import Fixtures
from utils    import mkfreshdir, run_git


class GitFixtures(Fixtures):

    """Methods to create and populate a git repository.

    git tests use this class in order to have something to test against.
    """

    def init(self):
        self.user_name  = 'test'
        self.user_email = 'test@test.com'
        self.create_repo(self.repo_path)
        self.wd = self.repo_path
        self.submodules_path = self.container_dir + '/submodules'

        # These will be two-level dicts; top level keys are
        # repo paths (this allows us to track the main repo
        # *and* submodules).
        self.timestamps = {}
        self.sha1s      = {}

        self.create_commits(2)

    def run(self, cmd):
        return run_git(cmd)

    def create_repo(self, repo_path):
        os.makedirs(repo_path)
        os.chdir(repo_path)
        self.safe_run('init')
        self.safe_run('config user.name  ' + self.user_name)
        self.safe_run('config user.email ' + self.user_email)
        print "created repo", repo_path

    def get_metadata(self, formatstr):
        return self.safe_run('log -n1 --pretty=format:"%s"' % formatstr)[0]

    def record_rev(self, wd, rev_num):
        tag = 'tag' + str(rev_num)
        self.safe_run('tag ' + tag)

        for d in (self.revs, self.timestamps, self.sha1s):
            if wd not in d:
                d[wd] = {}

        self.revs[wd][rev_num]   = tag
        self.timestamps[wd][tag] = self.get_metadata('%ct')
        self.sha1s[wd][tag]      = self.get_metadata('%H')
        self.scmlogs.annotate(
            "Recorded rev %d: id %s, timestamp %s, SHA1 %s in %s" %
            (rev_num,
             tag,
             self.timestamps[wd][tag],
             self.sha1s[wd][tag],
             wd)
        )

    def submodule_path(self, submodule_name):
        return self.submodules_path + '/' + submodule_name

    def create_submodule(self, submodule_name):
        path = self.submodule_path(submodule_name)
        # self.scmlogs.annotate("Creating repo in %s" % path)
        self.create_repo(path)
