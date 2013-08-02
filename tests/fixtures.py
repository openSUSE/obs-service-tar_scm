#!/usr/bin/python

import os
import shutil

class Fixtures:
    name  = 'tar_scm test suite'
    email = 'root@localhost'
    name_and_email = '%s <%s>' % (name, email)

    subdir = 'subdir'
    subdir1 = 'subdir1'
    subdir2 = 'subdir2'
    _next_commit_revs = { }

    def __init__(self, container_dir, scmlogs):
        self.container_dir = container_dir
        self.scmlogs       = scmlogs
        self.repo_path     = self.container_dir + '/repo'
        self.repo_url      = 'file://' + self.repo_path

        # Keys are stringified integers representing commit sequence numbers;
        # values can be passed to --revision
        self.revs = { }

    def setup(self):
        print self.__class__.__name__ + ": setting up fixtures"
        self.init_fixtures_dir()
        self.init()

    def init_fixtures_dir(self):
        if os.path.exists(self.repo_path):
            shutil.rmtree(self.repo_path)

    def init(self):
        raise NotImplementedError, \
            self.__class__.__name__ + " didn't implement init()"

    def create_commits(self, num_commits, wd=None):
        self.scmlogs.annotate("Creating %d commits ..." % num_commits)
        if num_commits == 0:
            return

        if wd is None:
            wd = self.wd
        os.chdir(wd)

        for i in xrange(0, num_commits):
            new_rev = self.create_commit(wd)
        self.record_rev(wd, new_rev)

        self.scmlogs.annotate("Created %d commits; now at %s" % (num_commits, new_rev))

    def next_commit_rev(self, wd):
        if wd not in self._next_commit_revs:
            self._next_commit_revs[wd] = 1
        new_rev = self._next_commit_revs[wd]
        self._next_commit_revs[wd] += 1
        return new_rev

    def create_commit(self, wd):
        new_rev = self.next_commit_rev(wd)
        newly_created = self.prep_commit(new_rev)
        self.do_commit(wd, new_rev, newly_created)
        return new_rev

    def do_commit(self, wd, new_rev, newly_created):
        self.run('add .')
        self.run('commit -m%d' % new_rev)

    def prep_commit(self, new_rev):
        """
        Caller should ensure correct cwd.
        Returns list of newly created files.
        """
        newly_created = [ ]

        if not os.path.exists('a'):
            newly_created.append('a')

        if not os.path.exists(self.subdir):
            os.mkdir(self.subdir)
            # This will take care of adding subdir/b too
            newly_created.append(self.subdir)

        for fn in ('a', self.subdir + '/b'):
            f = open(fn, 'w')
            f.write(str(new_rev))
            f.close()
            self.scmlogs.annotate("Wrote %s to %s" % (new_rev, fn))

        return newly_created
