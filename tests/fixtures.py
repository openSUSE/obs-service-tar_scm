#!/usr/bin/env python2

import os
import shutil
import re
from utils import run_cmd


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
        self.user_name  = 'test'
        self.user_email = 'test@test.com'
        self.container_dir = container_dir
        self.scmlogs       = scmlogs
        self.repo_path     = self.container_dir + '/repo'
        self.repo_url      = 'file://' + self.repo_path
        self.gpg_dir       = None
        self.gpg_key_id    = None

        # Keys are stringified integers representing commit sequence numbers;
        # values can be passed to --revision
        self.revs = {}

    def safe_run(self, cmd):
        if self.gpg_dir != None:
            os.putenv('GNUPGHOME', self.gpg_dir)

        stdout, stderr, exitcode = self.run(cmd)
        if exitcode != 0:
            raise RuntimeError("Command failed; aborting.")
        return stdout, stderr, exitcode

    def setup(self):
        print self.__class__.__name__ + ": setting up fixtures"
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

        for i in xrange(0, num_commits):
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

    def create_gpg_key(self):

        if self.gpg_dir:
            print 'GPG state already initialised'
            return (self.gpg_dir, self.gpg_key_id)

        batch_script = '''
            %echo starting keygen
            Key-Type: default
            Subkey-Type: default
            Name-Real: ''' + self.user_name + '''
            Name-Comment: test user
            Name-Email: ''' + self.user_email + '''
            Expire-Date: 1d
            %no-protection
            %transient-key
            %commit
            %echo done'''

        # create a dir to use as GNUPGHOME for key import and verification
        gpg_dir = self.container_dir + "/gpg"
        os.makedirs(gpg_dir)
        batch_path = gpg_dir + "/batch_script.txt"

        with open(batch_path, "w") as text_file:
            text_file.write(batch_script)

        cmd = 'gpg --homedir %s --gen-key --batch %s' % (gpg_dir, batch_path)
        (stdout, stderr, ret) = run_cmd(cmd)
        if ret != 0:
            print "GPG key creation failed: ", stderr
            return (None, None)

        cmd = 'gpg --homedir %s --keyid-format LONG --list-secret-keys' \
                % (gpg_dir)

        (stdout, stderr, ret) = run_cmd(cmd)
        if ret != 0:
            print "GPG key list failed: ", stderr
            return (None, None)

        m = re.search('sec\s+\w+/(\w+)', stdout)
        if m == None or m.group(1) == None:
            print "couldn't find GPG key ID in ", stdout
            return (None, None)

        gpg_key_id = m.group(1)

        print "created GPG keypair at %s with key id %s" % (gpg_dir, gpg_key_id)
        self.gpg_dir = gpg_dir
        self.gpg_key_id = gpg_key_id
        return (gpg_dir, gpg_key_id)

    def delete_gpg_key(self):
        if self.gpg_dir == None:
            return

        shutil.rmtree(self.gpg_dir)
        self.gpg_dir = None
        self.gpg_key_id = None
