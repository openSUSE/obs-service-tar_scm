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
    next_commit_rev = 1

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

    def create_commits(self, num_commits):
        self.scmlogs.annotate("Creating %d commits ..." % num_commits)
        if num_commits == 0:
            return

        for i in xrange(0, num_commits):
            new_rev = self.create_commit()
        self.record_rev(new_rev)

        self.scmlogs.annotate("Created %d commits; now at %s" % (num_commits, new_rev))

    def create_commit(self):
        os.chdir(self.wd)
        newly_created = self.prep_commit()
        self.do_commit(newly_created)
        new_rev = self.next_commit_rev
        self.next_commit_rev += 1
        return new_rev

    def prep_commit(self):
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
            f.write(str(self.next_commit_rev))
            f.close()

        return newly_created
