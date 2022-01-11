#!/usr/bin/env python

import os
import stat
from datetime import datetime

from utils    import mkfreshdir, quietrun, run_svn, file_write_legacy
from fixtures import Fixtures


class SvnFixtures(Fixtures):

    """Methods to create and populate a svn repository.

    svn tests use this class in order to have something to test against.
    """

    SVN_COMMITTER_DATE = datetime.utcfromtimestamp(
        Fixtures.COMMITTER_DATE).isoformat() + ".000000Z"

    def init(self):
        self.wd_path = self.container_dir + '/wd'
        self.user_name  = 'test'
        self.user_email = 'test@test.com'

        self.create_repo()
        self.checkout_repo()

        self.added = {}

        self.create_commits(2)

    def run(self, cmd):
        return run_svn(self.wd_path, cmd)

    def create_repo(self):
        quietrun('svnadmin create ' + self.repo_path)
        # allow revprop changes to explicitly set svn:date
        hook = self.repo_path + '/hooks/pre-revprop-change'
        file_write_legacy(hook, "#!/bin/sh\nexit 0;\n")

        sta = os.stat(hook)
        os.chmod(hook, sta.st_mode | stat.S_IEXEC)
        print("created repo %s" % self.repo_path)

    def checkout_repo(self):
        mkfreshdir(self.wd_path)
        quietrun('svn checkout %s %s' % (self.repo_url, self.wd_path))
        self.wdir = self.wd_path

    def do_commit(self, wdir, new_rev, newly_created):  # pylint: disable=W0612
        for new in newly_created:
            if new not in self.added:
                self.safe_run('add ' + new)
                self.added[new] = True
        self.safe_run('commit -m%d' % new_rev)
        self.safe_run('propset svn:date --revprop -r HEAD %s' %
                      self.SVN_COMMITTER_DATE)
        return new_rev

    def get_metadata(self, formatstr):
        return self.safe_run("log -n1 %s" % formatstr)[0]

    def record_rev(self, *args):
        rev_num = args[0]
        self.revs[rev_num] = str(rev_num)
        self.scmlogs.annotate("Recorded rev %d" % rev_num)
