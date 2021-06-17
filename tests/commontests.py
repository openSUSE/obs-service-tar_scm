#!/usr/bin/env python

import os
import tarfile


from pprint         import pprint, pformat

from tests.testassertions import TestAssertions
from tests.testenv        import TestEnvironment
from tests.utils          import mkfreshdir, run_cmd


class CommonTests(TestEnvironment, TestAssertions):

    """Unit tests common to all version control systems.

    Unit tests here are not specific to any particular version control
    system, and will be run for all of git / hg / svn / bzr.
    """

    def basename(self, name='repo', version=None):
        if version is None:
            version = self.default_version()
        return '%s-%s' % (name, version)

    def test_plain(self):
        self.tar_scm_std()
        self.assertTarOnly(self.basename())

    def test_symlink(self):
        self.fixtures.create_commits(1)
        self.tar_scm_std('--versionformat', '3',
                         '--revision', self.rev(3))
        basename   = self.basename(version=3)
        tar_handle = self.assertTarOnly(basename)
        # tarfile.extractfile() in python 2.6 is broken when extracting
        # relative symlinks as a file object so we construct linkname manually
        member = tar_handle.getmember(basename + '/c')
        self.assertTrue(member.issym())
        self.assertEquals(member.linkname, 'a')
        linkname = '/'.join([os.path.dirname(member.name), member.linkname])
        self.assertTarMemberContains(tar_handle, linkname, '3')

    def test_broken_symlink(self):
        self.fixtures.create_commit_broken_symlink()
        self.tar_scm_std('--versionformat', '3',
                         '--revision', self.rev(3))
        basename   = self.basename(version=3)
        tar_handle = self.assertTarOnly(basename)
        member     = tar_handle.getmember(basename + '/c')
        self.assertTrue(member.issym())
        self.assertRegexpMatches(member.linkname, '[/.]*/nir/va/na$')

    def test_tar_exclude(self):
        self.tar_scm_std('--exclude', 'a', '--exclude', 'c')
        tar     = os.path.join(self.outdir, self.basename()+'.tar')
        th      = tarfile.open(tar)
        tarents = th.getnames()
        expected = [self.basename(),
                    self.basename() + '/subdir',
                    self.basename() + '/subdir/b']
        self.assertTrue(tarents == expected)

    def test_tar_include(self):
        self.tar_scm_std('--include', self.fixtures.subdir)
        tar     = os.path.join(self.outdir, self.basename()+'.tar')
        th      = tarfile.open(tar)
        tarents = th.getnames()
        expected = [self.basename(),
                    self.basename() + '/subdir',
                    self.basename() + '/subdir/b']
        self.assertTrue(tarents == expected)

    def test_obs_scm_exclude(self):
        self.tar_scm_std('--exclude', 'a', '--exclude', 'c', '--use-obs-scm', 'True')
        cpio    = os.path.join(self.outdir, self.basename()+'.obscpio')
        cmd = "cpio -it < "+cpio
        (stdout, stderr, ret) = run_cmd(cmd)
        got = stdout.decode().split("\n")
        got.pop()
        expected = [self.basename() + '/subdir',
                    self.basename() + '/subdir/b']
        self.assertTrue(got == expected)

    def test_obs_scm_include(self):
        self.tar_scm_std('--include', self.fixtures.subdir, '--use-obs-scm', 'True')
        cpio    = os.path.join(self.outdir, self.basename()+'.obscpio')
        cmd = "cpio -it < "+cpio
        (stdout, stderr, ret) = run_cmd(cmd)
        got = stdout.decode().split("\n")
        got.pop()
        expected = [self.basename() + '/subdir',
                    self.basename() + '/subdir/b']
        self.assertTrue(got == expected)


    def test_absolute_subdir(self):
        (_stdout, stderr, _ret) = self.tar_scm_std_fail('--subdir', '/')
        self.assertRegexpMatches(
            stderr, "Absolute path '/' is not allowed for --subdir")

    def test_subdir_parent(self):
        for path in ('..', '../', '../foo', 'foo/../../bar'):
            (_stdout, stderr, _ret) = self.tar_scm_std_fail('--subdir', path)
            self.assertRegexpMatches(
                stderr, "--subdir path '%s' must stay within repo" % path)

    def test_extract_parent(self):
        for path in ('..', '../', '../foo', 'foo/../../bar'):
            (_stdout, stderr, _ret) = self.tar_scm_std_fail('--extract', path)
            self.assertRegexpMatches(
                stderr, '--extract is not allowed to contain ".."')

    def test_filename(self):
        for path in ('/tmp/somepkg.tar', '../somepkg.tar'):
            (_stdout, stderr, _ret) = self.tar_scm_std_fail('--filename', path)
            self.assertRegexpMatches(
                stderr, '--filename must not specify a path')

    def test_subdir(self):
        self.tar_scm_std('--subdir', self.fixtures.subdir)
        self.assertTarOnly(self.basename(), tarchecker=self.assertSubdirTar)

    def test_history_depth_obsolete(self):
        (stdout, _stderr, _ret) = self.tar_scm_std('--history-depth', '1')
        self.assertRegexpMatches(stdout, 'obsolete')

    def test_filename(self):
        name = 'myfilename'
        self.tar_scm_std('--filename', name)
        self.assertTarOnly(self.basename(name=name))

    def test_version(self):
        version = '0.5'
        self.tar_scm_std('--version', version)
        self.assertTarOnly(self.basename(version=version))

    def test_filename_version(self):
        filename = 'myfilename'
        version = '0.6'
        self.tar_scm_std('--filename', filename, '--version', version)
        self.assertTarOnly(self.basename(filename, version))

    def test_filename_without_version(self):
        filename = 'myfilename'
        self.fixtures.create_commits(1)
        self.tar_scm_std('--filename', filename, '--version', '_none_')
        self.assertTarOnly(filename)

    def test_revision_nop(self):
        self.tar_scm_std('--revision', self.rev(2))
        tar_handle = self.assertTarOnly(self.basename())
        self.assertTarMemberContains(tar_handle, self.basename() + '/a', '2')

    def test_revision(self):
        self._revision()

    def test_revision_lang_de(self):
        os.putenv('LANG', 'de_DE.UTF-8')
        os.environ['LANG'] = 'de_DE.UTF-8'
        self._revision()
        os.unsetenv('LANG')
        os.environ['LANG'] = ''

    def test_revision_no_cache(self):
        self._revision(use_cache=False)

    def test_revision_subdir(self):
        self._revision(use_subdir=True)

    def test_revision_subdir_no_cache(self):
        self._revision(use_cache=False, use_subdir=True)

    def _revision(self, use_cache=True, use_subdir=False):
        """
        Check that the right revision is packaged up, regardless of
        whether new commits have been introduced since previous runs.
        """
        version = '3.0'
        args_tag2 = [
            '--version', version,
            '--revision', self.rev(2),
        ]
        if use_subdir:
            args_tag2 += ['--subdir', self.fixtures.subdir]
        self._sequential_calls_with_revision(
            version,
            [
                (0, args_tag2, '2', False),
                (0, args_tag2, '2', use_cache),
                (2, args_tag2, '2', use_cache),
                (0, args_tag2, '2', use_cache),
                (2, args_tag2, '2', use_cache),
                (0, args_tag2, '2', use_cache),
            ],
            use_cache
        )

    def test_rev_alter(self):
        self._revision_master_alternating()

    def test_rev_alter_no_cache(self):
        self._revision_master_alternating(use_cache=False)

    def test_rev_alter_subdir(self):
        self._revision_master_alternating(use_subdir=True)

    def test_rev_alter_subdir_no_cache(self):
        self._revision_master_alternating(use_cache=False, use_subdir=True)

    def _revision_master_alternating(self, use_cache=True, use_subdir=False):
        """
        Call tar_scm 7 times, alternating between a specific revision
        and the default branch (master), and checking the results each
        time.  New commits are created before some of the invocations.
        """
        version = '4.0'
        args_head = [
            '--version', version,
        ]
        if use_subdir:
            args_head += ['--subdir', self.fixtures.subdir]

        args_tag2 = args_head + ['--revision', self.rev(2)]
        self._sequential_calls_with_revision(
            version,
            [
                (0, args_tag2, '2', False),
                (0, args_head, '2', use_cache),
                (2, args_tag2, '2', use_cache),
                (0, args_head, '4', use_cache),
                (2, args_tag2, '2', use_cache),
                (0, args_head, '6', use_cache),
                (0, args_tag2, '2', use_cache),
            ],
            use_cache
        )

    def _sequential_calls_with_revision(self, version, calls, use_cache=True):
        """
        Call tar_scm a number of times, optionally creating some
        commits before each invocation, and checking that the result
        contains the right revision after each invocation.
        """
        mkfreshdir(self.pkgdir)
        basename = self.basename(version=version)

        if not use_cache:
            self.disableCache()

        step_number = 0
        while calls:
            step_number += 1
            new_commits, args, expected, expect_cache_hit = calls.pop(0)
            if new_commits > 0:
                self.fixtures.create_commits(new_commits)
            self.scmlogs.annotate(
                "step #%s: about to run tar_scm with args: %s" %
                (step_number, pformat(args)))
            self.scmlogs.annotate("expecting tar to contain: " + expected)
            self.tar_scm_std(*args)
            logpath = self.scmlogs.current_log_path
            loglines = self.scmlogs.read()
            if expect_cache_hit:
                self.assertRanUpdate(logpath, loglines)
            else:
                self.assertRanInitialClone(logpath, loglines)

            if self.fixtures.subdir in args:
                tar_handle = self.assertTarOnly(
                    basename,
                    tarchecker=self.assertSubdirTar
                )
                tarent = 'b'
            else:
                tar_handle = self.assertTarOnly(basename)
                tarent = 'a'
            self.assertTarMemberContains(
                tar_handle,
                basename + '/' + tarent,
                expected
            )

            self.scmlogs.next()
            self.postRun()

    def test_switch_revision_and_subdir(self):
        self._switch_revision_and_subdir()

    def test_switch_rev_and_subdir_nc(self):
        self._switch_revision_and_subdir(use_cache=False)

    def _switch_revision_and_subdir(self, use_cache=True):
        version = '5.0'
        args = [
            '--version', version,
        ]
        args_subdir = args + ['--subdir', self.fixtures.subdir]

        args_tag2 = args + ['--revision', self.rev(2)]
        self._sequential_calls_with_revision(
            version,
            [
                (0, args_tag2,   '2', False),
                (0, args_subdir, '2', use_cache and self.scm != 'svn'),
                (2, args_tag2,   '2', use_cache),
                (0, args_subdir, '4', use_cache),
                (2, args_tag2,   '2', use_cache),
                (0, args_subdir, '6', use_cache),
                (0, args_tag2,   '2', use_cache),
            ],
            use_cache
        )

    def test_sslverify_disabled(self):
        self.tar_scm_std('--sslverify', 'disable')
        logpath = self.scmlogs.current_log_path
        loglines = self.scmlogs.read()
        self.assertRanInitialClone(logpath, loglines)
        self.assertSSLVerifyFalse(logpath, loglines)

    def test_sslverify_enabled(self):
        self.tar_scm_std('--sslverify', 'enable')
        logpath = self.scmlogs.current_log_path
        loglines = self.scmlogs.read()
        self.assertRanInitialClone(logpath, loglines)
