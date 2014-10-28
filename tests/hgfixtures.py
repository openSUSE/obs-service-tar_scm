#!/usr/bin/env python2

import os

from fixtures import Fixtures
from utils    import mkfreshdir, run_hg


class HgFixtures(Fixtures):

    """Methods to create and populate a mercurial repository.

    mercurial tests use this class in order to have something to test against.
    """

    def init(self):
        self.create_repo()

        self.timestamps  = {}
        self.sha1s       = {}
        self.short_sha1s = {}

        self.create_commits(2)

    def run(self, cmd):
        return run_hg(self.repo_path, cmd)

    def create_repo(self):
        os.makedirs(self.repo_path)
        os.chdir(self.repo_path)
        self.safe_run('init')
        c = open('.hg/hgrc', 'w')
        c.write("[ui]\nusername = %s\n" % self.name_and_email)
        c.close()
        self.wd = self.repo_path
        print "created repo", self.repo_path

    def get_metadata(self, formatstr):
        return self.safe_run('log -l1 --template "%s"' % formatstr)[0]

    def record_rev(self, wd, rev_num):
        tag = str(rev_num - 1)  # hg starts counting changesets at 0
        self.revs[rev_num] = tag
        epoch_secs, tz_delta_to_utc = \
            self.get_metadata('{date|hgdate}').split()
        self.timestamps[tag] = (float(epoch_secs), int(tz_delta_to_utc))
        self.sha1s[tag] = self.get_metadata('{node}')
        self.short_sha1s[tag] = self.get_metadata('{node|short}')
        self.scmlogs.annotate(
            "Recorded rev %d: id %s, timestamp %s, SHA1 %s" %
            (rev_num,
             tag,
             self.timestamps[tag],
             self.sha1s[tag])
        )
