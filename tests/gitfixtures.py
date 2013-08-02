#!/usr/bin/python

import os

from   fixtures  import Fixtures
from   utils     import mkfreshdir, run_git

class GitFixtures(Fixtures):
    def init(self):
        self.create_repo(self.repo_path)
        self.wd = self.repo_path

        self.timestamps   = { }
        self.sha1s        = { }

        self.create_commits(2)

    def run(self, cmd):
        return run_git(self.repo_path, cmd)

    def create_repo(self, repo_path):
        os.makedirs(repo_path)
        os.chdir(repo_path)
        self.run('init')
        self.run('config user.name test')
        self.run('config user.email test@test.com')
        print "created repo", repo_path

    def do_commit(self, newly_created):
        self.run('add .')
        self.run('commit -m%d' % self.next_commit_rev)

    def get_metadata(self, formatstr):
        return self.run('log -n1 --pretty=format:"%s"' % formatstr)[0]

    def record_rev(self, rev_num):
        tag = 'tag' + str(rev_num)
        self.run('tag ' + tag)
        self.revs[rev_num]   = tag
        self.timestamps[tag] = self.get_metadata('%ct')
        self.sha1s[tag]      = self.get_metadata('%h')
        self.scmlogs.annotate(
            "Recorded rev %d: id %s, timestamp %s, SHA1 %s" % \
                (rev_num,
                 tag,
                 self.timestamps[tag],
                 self.sha1s[tag])
        )
