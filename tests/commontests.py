#!/usr/bin/python

import os

from pprint         import pprint, pformat

from testassertions import TestAssertions
from testenv        import TestEnvironment
from utils          import mkfreshdir

class CommonTests(TestEnvironment, TestAssertions):
    def default_name(self):
        return "repo"

    def basename(self, name=None, version=None):
        if name is None:
            name = self.default_name()
        if version is None:
            version = self.default_version()
        return '%s-%s' % (name, version)

    def test_plain(self):
        self.tar_scm_std()
        self.assertTarOnly(self.basename())

    def test_exclude(self):
        self.tar_scm_std('--exclude', '.' + self.scm)
        self.assertTarOnly(self.basename())

    def test_subdir(self):
        self.tar_scm_std('--subdir', self.fixtures.subdir)
        self.assertTarOnly(self.basename(), tarchecker=self.assertSubdirTar)

    def test_history_depth_obsolete(self):
        (stdout, stderr, ret) = self.tar_scm_std('--history-depth', '1')
        self.assertRegexpMatches(stdout, 'obsolete')
        # self.assertTarOnly(self.basename())
        # self.assertRegexpMatches(self.scmlogs.read()[0], '^%s clone --depth=1')

    # def test_history_depth_full(self):
    #     self.tar_scm_std('--history-depth', 'full')
    #     self.assertTarOnly(self.basename())
    #     self.assertRegexpMatches(self.scmlogs.read()[0], '^git clone --depth=999999+')

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

    def test_tarfilename(self):
        filename = 'myfilename'
        version = '0.7'
        tarfilename = '${NAME}-${VERSION}'
        tarbasename = filename + "-" + version
        self.tar_scm_std('--filename', filename, '--version', version, '--tarfilename', tarfilename)
        self.assertTarOnly( tarbasename = tarbasename, toptardir = self.basename(filename, version) )

    def test_tarfilename_NAME_VERSION_defaults(self):
        tarfilename = '${NAME}_${VERSION}'
        tarbasename = self.default_name() + "_" + self.default_version()
        self.tar_scm_std( '--tarfilename', tarfilename)
        self.assertTarOnly( tarbasename = tarbasename, toptardir = self.basename() )

    def test_tarfilename_NAME_VERSION(self):
        filename = 'myfilename'
        version = '0.7'
        tarfilename = '${NAME}_${VERSION}'
        tarbasename = filename + "_" + version
        self.tar_scm_std('--filename', filename, '--version', version, '--tarfilename', tarfilename)
        self.assertTarOnly( tarbasename = tarbasename, toptardir = self.basename(filename, version) )

    def test_tarfilename_NAME_VERSION_orig(self):
        filename = 'myfilename'
        version = '0.7'
        tarfilename = '${NAME}_${VERSION}.orig'
        tarbasename = filename + "_" + version + ".orig"
        self.tar_scm_std('--filename', filename, '--version', version, '--tarfilename', tarfilename)
        self.assertTarOnly( tarbasename = tarbasename, toptardir = self.basename(filename, version) )

    def test_revision_nop(self):
        self.tar_scm_std('--revision', self.rev(2))
        th = self.assertTarOnly(self.basename())
        self.assertTarMemberContains(th, self.basename() + '/a', '2')

    def test_revision(self):
        self._revision()

    def test_revision_lang_de(self):
        os.putenv('LANG', 'de_DE.UTF-8')
        self._revision()
        os.unsetenv('LANG')

    def test_revision_no_cache(self):
        self._revision(use_cache=False)

    def test_revision_subdir(self):
        self._revision(use_subdir=True)

    def test_revision_subdir_no_cache(self):
        self._revision(use_cache=False, use_subdir=True)

    def _revision(self, use_cache=True, use_subdir=False):
        version = '3.0'
        args_tag2 = [
            '--version', version,
            '--revision', self.rev(2),
        ]
        if use_subdir:
            args_tag2 += [ '--subdir', self.fixtures.subdir ]
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

    def test_revision_master_alternating(self):
        self._revision_master_alternating()

    def test_revision_master_alternating_no_cache(self):
        self._revision_master_alternating(use_cache=False)

    def test_revision_master_alternating_subdir(self):
        self._revision_master_alternating(use_subdir=True)

    def test_revision_master_alternating_subdir_no_cache(self):
        self._revision_master_alternating(use_cache=False, use_subdir=True)

    def _revision_master_alternating(self, use_cache=True, use_subdir=False):
        version = '4.0'
        args_head = [
            '--version', version,
        ]
        if use_subdir:
            args_head += [ '--subdir', self.fixtures.subdir ]
        
        args_tag2 = args_head + [ '--revision', self.rev(2) ]
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
        mkfreshdir(self.pkgdir)
        basename = self.basename(version = version)

        if not use_cache:
            self.disableCache()

        step_number = 0
        while calls:
            step_number += 1
            new_commits, args, expected, expect_cache_hit = calls.pop(0)
            if new_commits > 0:
                self.fixtures.create_commits(new_commits)
            self.scmlogs.annotate("step #%s: about to run tar_scm with args: %s" %
                                  (step_number, pformat(args)))
            self.scmlogs.annotate("expecting tar to contain: " + expected)
            self.tar_scm_std(*args)
            logpath  = self.scmlogs.current_log_path
            loglines = self.scmlogs.read()
            if expect_cache_hit:
                self.assertRanUpdate(logpath, loglines)
            else:
                self.assertRanInitialClone(logpath, loglines)

            if self.fixtures.subdir in args:
                th = self.assertTarOnly(basename, tarchecker=self.assertSubdirTar)
                tarent = 'b'
            else:
                th = self.assertTarOnly(basename)
                tarent = 'a'
            self.assertTarMemberContains(th, basename + '/' + tarent, expected)

            self.scmlogs.next()
            self.postRun()

    def test_switch_revision_and_subdir(self):
        self._switch_revision_and_subdir()

    def test_switch_revision_and_subdir_no_cache(self):
        self._switch_revision_and_subdir(use_cache=False)

    def _switch_revision_and_subdir(self, use_cache=True):
        version = '5.0'
        args = [
            '--version', version,
        ]
        args_subdir = args+ [ '--subdir', self.fixtures.subdir ]
        
        args_tag2 = args + [ '--revision', self.rev(2) ]
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
