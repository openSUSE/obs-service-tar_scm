#!/usr/bin/env python

import os

from fixtures import Fixtures
from utils    import run_git


class GitFixtures(Fixtures):

    """Methods to create and populate a git repository.

    git tests use this class in order to have something to test against.
    """

    def init(self):
        self.user_name  = 'test'
        self.user_email = 'test@test.com'

        tmpdir = os.path.join(os.path.dirname(
            os.path.abspath(__file__)), 'tmp')
        gitconfig = os.path.join(tmpdir, '.gitconfig')
        os.environ["GIT_CONFIG_GLOBAL"] = gitconfig
        self.safe_run('config --global protocol.file.allow always')
        self.safe_run('config --global commit.gpgsign false')

        self.create_repo(self.repo_path)
        self.wdir = self.repo_path
        self.submodules_path = self.container_dir + '/submodules'

        # These will be two-level dicts; top level keys are
        # repo paths (this allows us to track the main repo
        # *and* submodules).
        self.timestamps = {}
        self.sha1s      = {}

        # Force the committer timestamp to our well known default
        os.environ["GIT_COMMITTER_DATE"] = self.get_committer_date()

        self.create_commits(2)

    def run(self, cmd):  # pylint: disable=R0201
        return run_git(cmd)

    def create_repo(self, repo_path):
        os.makedirs(repo_path)
        os.chdir(repo_path)
        self.safe_run('init')
        self.safe_run('config user.name  ' + self.user_name)
        self.safe_run('config user.email ' + self.user_email)
        print("created repo %s" % repo_path)

    def get_metadata(self, fmt):
        return self.safe_run('log -n1 --pretty=format:"%s"' % fmt)[0].decode()

    def record_rev(self, rev_num, *args):
        wdir = args[0]
        print(" ****** wdir: %s" % wdir)
        tag = 'tag' + str(rev_num)
        self.safe_run('tag ' + tag)

        for dname in (self.revs, self.timestamps, self.sha1s):
            if wdir not in dname:
                dname[wdir] = {}

        self.revs[wdir][rev_num]   = tag
        self.timestamps[wdir][tag] = self.get_metadata('%ct')
        self.sha1s[wdir][tag]      = self.get_metadata('%H')
        self.scmlogs.annotate(
            "Recorded rev %d: id %s, timestamp %s, SHA1 %s in %s" %
            (rev_num,
             tag,
             self.timestamps[wdir][tag],
             self.sha1s[wdir][tag],
             wdir)
        )

    def submodule_path(self, submodule_name):
        return self.submodules_path + '/' + submodule_name

    def create_submodule(self, submodule_name):
        path = self.submodule_path(submodule_name)
        # self.scmlogs.annotate("Creating repo in %s" % path)
        self.create_repo(path)
