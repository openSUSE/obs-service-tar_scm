# -*- coding: utf-8 -*-
# pylint: disable=R0902

import os
import shutil
import io

from utils import file_write_legacy

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
        self.wdir          = None
        self.user_name     = None
        self.user_email    = None
        self.timestamps    = None
        self.sha1s         = None
        self.short_sha1s   = None
        self.wd_path       = None
        self.added         = None
        self.submodules_path = None


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

    def create_commits(self, num_commits, wdir=None, subdir=None):
        self.scmlogs.annotate("Creating %d commits ..." % num_commits)
        if num_commits == 0:
            return

        if wdir is None:
            wdir = self.wdir
        orig_wd = os.getcwd()
        os.chdir(wdir)

        for inc in range(0, num_commits):  # pylint: disable=W0612
            new_rev = self.create_commit(wdir, subdir=subdir)
        self.record_rev(new_rev, wdir)

        self.scmlogs.annotate("Created %d commits; now at %s" %
                              (num_commits, new_rev))
        os.chdir(orig_wd)

    def next_commit_rev(self, wdir):
        if wdir not in self._next_commit_revs:
            self._next_commit_revs[wdir] = 1
        new_rev = self._next_commit_revs[wdir]
        self._next_commit_revs[wdir] += 1
        return new_rev

    def create_commit(self, wdir, subdir=None):
        new_rev = self.next_commit_rev(wdir)
        newly_created = self.prep_commit(new_rev, subdir=subdir)
        self.do_commit(wdir, new_rev, newly_created)
        return new_rev

    def do_commit(self, wdir, new_rev, newly_created):  # pylint: disable=W0613
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

        for fname in ('a', subdir + '/b'):
            file_write_legacy(fname, new_rev)
            self.scmlogs.annotate("Wrote %s to %s" % (new_rev, fname))

        # we never commit through symlink 'c' but instead see the updated
        # revision through the symlink
        if not os.path.lexists('c'):
            os.symlink('a', 'c')
            newly_created.append('c')

        return newly_created

    def create_commit_broken_symlink(self, wdir=None):
        self.scmlogs.annotate("Creating broken symlink commit")

        if wdir is None:
            wdir = self.wdir
        os.chdir(wdir)

        new_rev = self.next_commit_rev(wdir)
        newly_created = self.prep_commit(new_rev)
        os.unlink('c')
        os.symlink('/../nir/va/na', 'c')
        newly_created.append('c')
        self.do_commit(wdir, new_rev, newly_created)
        self.record_rev(new_rev, wdir)
        self.scmlogs.annotate("Created 1 commit; now at %s" % (new_rev))

    def create_commit_unicode(self, wdir=None):
        self.scmlogs.annotate("Creating commit with unicode commit message")

        if wdir is None:
            wdir = self.wdir
        os.chdir(wdir)

        new_rev = self.next_commit_rev(wdir)
        fname = 'd'
        file_write_legacy(fname, new_rev)
        self.scmlogs.annotate("Wrote %s to %s" % (new_rev, fname))
        self.safe_run('add .')
        date = self.get_committer_date()
        self.safe_run('commit -m"füfüfü nününü %d" %s' % (new_rev, date))
        self.record_rev(new_rev, wdir)
        self.scmlogs.annotate("Created 1 commit; now at %s" % (new_rev))

    def touch(self, fname, times=None):
        fpath = os.path.join(self.wdir, fname)
        with io.open(fpath, 'a', encoding='UTF-8'):
            os.utime(fname, times)

    def remove(self, fname):
        os.remove(os.path.join(self.wdir, fname))

    def tag(self, tag):
        self.safe_run('tag %s' % tag)

    def commit_file_with_tag(self, tag, file):
        self.touch(file)
        self.create_commit(self.wdir)
        self.tag(tag)
