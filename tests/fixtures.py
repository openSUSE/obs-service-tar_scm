#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import shutil


class Fixtures:

    """Base class for all fixture classes."""

    name  = 'tar_scm test suite'
    email = 'root@localhost'
    name_and_email = '%s <%s>' % (name, email)

    subdir = 'subdir'
    subdir1 = 'subdir1'
    subdir2 = 'subdir2'
    _next_commit_revs = {}

    # the timestamp (in seconds since epoch ) that should be used for commits
    COMMITTER_DATE = int(1234567890)

    def __init__(self, container_dir, scmlogs):
        self.container_dir = container_dir
        self.scmlogs       = scmlogs
        self.repo_path     = self.container_dir + '/repo'
        self.repo_url      = 'file://' + self.repo_path

        # Keys are stringified integers representing commit sequence numbers;
        # values can be passed to --revision
        self.revs = {}

    def safe_run(self, cmd):
        stdout, stderr, exitcode = self.run(cmd)
        if exitcode != 0:
            raise RuntimeError("Command failed; aborting.")
        return stdout, stderr, exitcode

    def setup(self):
        print(self.__class__.__name__ + ": setting up fixtures")
        self.init_fixtures_dir()
        self.init()

    def init_fixtures_dir(self):
        if os.path.exists(self.repo_path):
            shutil.rmtree(self.repo_path)

    def init(self):
        raise NotImplementedError(
            self.__class__.__name__ + " didn't implement init()")

    def create_commits(self, num_commits, wd=None, subdir=None):
        self.scmlogs.annotate("Creating %d commits ..." % num_commits)
        if num_commits == 0:
            return

        if wd is None:
            wd = self.wd
        orig_wd = os.getcwd()
        os.chdir(wd)

        for i in range(0, num_commits):
            new_rev = self.create_commit(wd, subdir=subdir)
        self.record_rev(wd, new_rev)

        self.scmlogs.annotate("Created %d commits; now at %s" %
                              (num_commits, new_rev))
        os.chdir(wd)

    def next_commit_rev(self, wd):
        if wd not in self._next_commit_revs:
            self._next_commit_revs[wd] = 1
        new_rev = self._next_commit_revs[wd]
        self._next_commit_revs[wd] += 1
        return new_rev

    def create_commit(self, wd, subdir=None):
        new_rev = self.next_commit_rev(wd)
        newly_created = self.prep_commit(new_rev, subdir=subdir)
        self.do_commit(wd, new_rev, newly_created)
        return new_rev

    def do_commit(self, wd, new_rev, newly_created):
        self.safe_run('add .')
        date = self.get_committer_date()
        self.safe_run('commit -m%d %s' % (new_rev, date))

    def get_committer_date(self):
        return '--date="%s"' % str(self.COMMITTER_DATE)

    def prep_commit(self, new_rev, subdir=None):
        """
        Caller should ensure correct cwd.
        Returns list of newly created files.
        """
        if not subdir:
            subdir = self.subdir
        self.scmlogs.annotate("cwd is %s" % os.getcwd())
        newly_created = []

        if not os.path.exists('a'):
            newly_created.append('a')

        if not os.path.exists(subdir):
            os.mkdir(subdir)
            # This will take care of adding subdir/b too
            newly_created.append(subdir)

        for fn in ('a', subdir + '/b'):
            f = open(fn, 'w')
            f.write(str(new_rev))
            f.close()
            self.scmlogs.annotate("Wrote %s to %s" % (new_rev, fn))

        # we never commit through symlink 'c' but instead see the updated
        # revision through the symlink
        if not os.path.lexists('c'):
            os.symlink('a', 'c')
            newly_created.append('c')

        return newly_created

    def create_commit_broken_symlink(self, wd=None):
        self.scmlogs.annotate("Creating broken symlink commit")

        if wd is None:
            wd = self.wd
        os.chdir(wd)

        new_rev = self.next_commit_rev(wd)
        newly_created = self.prep_commit(new_rev)
        os.unlink('c')
        os.symlink('/../nir/va/na', 'c')
        newly_created.append('c')
        self.do_commit(wd, new_rev, newly_created)
        self.record_rev(wd, new_rev)
        self.scmlogs.annotate("Created 1 commit; now at %s" % (new_rev))

    def create_commit_unicode(self, wd=None):
        self.scmlogs.annotate("Creating commit with unicode commit message")

        if wd is None:
            wd = self.wd
        os.chdir(wd)

        new_rev = self.next_commit_rev(wd)
        fname = 'd'
        cfh = open(fname, 'w')
        cfh.write(str(new_rev))
        cfh.close()
        self.scmlogs.annotate("Wrote %s to %s" % (new_rev, fname))
        #self.do_commit(wd, new_rev, newly_created)
        self.safe_run('add .')
        date = self.get_committer_date()
        self.safe_run('commit -m"füfüfü nününü %d" %s' % (new_rev, date))
        self.record_rev(wd, new_rev)
        self.scmlogs.annotate("Created 1 commit; now at %s" % (new_rev))
