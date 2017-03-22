#!/usr/bin/env python2

import unittest
import sys
import os
import re
import inspect
import copy
import subprocess
from mock import patch

import TarSCM
import argparse

from TarSCM.helpers import helpers
from TarSCM.config import config
from TarSCM.changes import changes
from TarSCM.scm.git import git
from TarSCM.scm.svn import svn
from TarSCM.archive import obscpio
from TarSCM.archive import tar


class UnitTestCases(unittest.TestCase):
    def setUp(self):
        self.cli            = TarSCM.cli()
        self.tasks          = TarSCM.tasks()
        self.tests_dir      = os.path.abspath(os.path.dirname(__file__))
        self.tmp_dir        = os.path.join(self.tests_dir, 'tmp')
        self.fixtures_dir   = os.path.join(self.tests_dir, 'fixtures',
                                           self.__class__.__name__)

        self.cli.parse_args(['--outdir', '.'])
        os.environ['CACHEDIRECTORY'] = ''

    def test_calc_dir_to_clone_to(self):
        scm = 'git'
        outdir = '/out/'

        clone_dirs = [
            '/local/repo.git',
            '/local/repo/.git',
            '/local/repo/.git/',
            'http://remote/repo.git;param?query#fragment',
            'http://remote/repo/.git;param?query#fragment',
        ]

        scm = TarSCM.scm.git(self.cli, self.tasks)

        for cd in clone_dirs:
            scm.url = cd
            scm._calc_dir_to_clone_to("")
            self.assertEqual(scm.clone_dir, os.path.join(scm.repodir))
            self.tasks.cleanup()

    @patch('TarSCM.helpers.safe_run')
    def test__git_log_cmd_with_args(self, safe_run_mock):
        scm     = TarSCM.scm.git(self.cli, self.tasks)
        new_cmd = scm._log_cmd(['-n1'], '')
        safe_run_mock.assert_called_once_with(['git', 'log', '-n1'], cwd=None)

    @patch('TarSCM.helpers.safe_run')
    def test__git_log_cmd_without_args(self, safe_run_mock):
        scm     = TarSCM.scm.git(self.cli, self.tasks)
        new_cmd = scm._log_cmd([], '')
        safe_run_mock.assert_called_once_with(['git', 'log'], cwd=None)

    @patch('TarSCM.helpers.safe_run')
    def test__git_log_cmd_with_subdir(self, safe_run_mock):
        scm     = TarSCM.scm.git(self.cli, self.tasks)
        new_cmd = scm._log_cmd(['-n1'], 'subdir')
        safe_run_mock.assert_called_once_with(['git', 'log', '-n1',
                                               '--', 'subdir'], cwd=None)

    def test_safe_run_exception(self):
        h = helpers()
        self.assertRaisesRegexp(
            SystemExit,
            re.compile("Command failed\(1\): ''"),
            h.safe_run,
            "/bin/false",
            cwd=None,
        )

    def test_TarSCM_config_files_ordering(self):
        tc_name = inspect.stack()[0][3]
        files = [
            [os.path.join(self.fixtures_dir, tc_name, 'a.cfg'), True],
            [os.path.join(self.fixtures_dir, tc_name, 'b.cfg'), True],
        ]
        var = config(files).get(None, 'var')
        self.assertEqual(var, 'b')

    def test_TarSCM_config_no_faked_header(self):
        tc_name = inspect.stack()[0][3]
        files   = [
            [os.path.join(self.fixtures_dir, tc_name, 'test.ini'), False]
        ]
        var     = config(files).get('general', 'apiurl')
        self.assertEqual(var, 'http://api.example.com')
        var     = config(files).get(var, 'email')
        self.assertEqual(var, 'devel@example.com')

    def test_TarSCM_config_debug_tar_scm(self):
        tc_name = inspect.stack()[0][3]

        try:
            tmp = os.environ['DEBUG_TAR_SCM']
        except KeyError:
            tmp = None

        os.environ['DEBUG_TAR_SCM'] = "1"

        files = [[os.path.join(self.fixtures_dir, tc_name, 'test.rc'), True]]
        var = config(files).get(None, 'var')
        self.assertEqual(var, None)

        if tmp:
            os.environ['DEBUG_TAR_SCM'] = tmp
        else:
            os.environ['DEBUG_TAR_SCM'] = ''
            os.unsetenv('DEBUG_TAR_SCM')

    def test_TarSCM_changes_get_changesauthor_from_args(self):
        c                   = changes()
        cli                 = copy.copy(self.cli)
        cli.changesauthor   = 'args@example.com'
        ca                  = c.get_changesauthor(cli)
        self.assertEqual(ca, 'args@example.com')

    def test_TarSCM_changes_get_changesauthor_from_oscrc(self):
        tc_name             = inspect.stack()[0][3]
        home                = os.environ['HOME']
        os.environ['HOME']  = os.path.join(self.fixtures_dir, tc_name)
        c                   = changes()
        ca                  = c.get_changesauthor(self.cli)
        os.environ['HOME']  = home
        self.assertEqual(ca, 'devel@example.com')

    def test_TarSCM_changes_get_changesauthor_default(self):
        home                = os.environ['HOME']
        os.environ['HOME']  = '/nir/va/na'
        c                   = changes()
        ca                  = c.get_changesauthor(self.cli)
        os.environ['HOME']  = home
        self.assertEqual(ca, 'opensuse-packaging@opensuse.org')

    def test_TarSCM_changes_get_changesauthor_from_home_rc(self):
        tc_name             = inspect.stack()[0][3]
        home                = os.environ['HOME']
        os.environ['HOME']  = os.path.join(self.fixtures_dir, tc_name)
        c                   = changes()
        ca                  = c.get_changesauthor(self.cli)
        os.environ['HOME']  = home
        self.assertEqual(ca, 'devel@example.com')

    def test_git_get_repocache_hash_without_subdir(self):
        scm_object = git(self.cli, self.tasks)
        scm_object.url = 'https://github.com/openSUSE/obs-service-tar_scm.git'
        repohash = scm_object.get_repocache_hash(None)
        self.assertEqual(
            repohash,
            'c0f3245498ad916e9ee404acfd7aa59e29d53b7a063a8609735c1284c67b2161')

    def test_git_get_repocache_hash_with_subdir(self):
        '''
        This test case proves that subdir is ignored in
        TarSCM.base.scm.get_repocache_hash
        '''
        scm_object = git(self.cli, self.tasks)
        scm_object.url = 'https://github.com/openSUSE/obs-service-tar_scm.git'
        repohash = scm_object.get_repocache_hash('subdir')
        self.assertEqual(
            repohash,
            'c0f3245498ad916e9ee404acfd7aa59e29d53b7a063a8609735c1284c67b2161')

    def test_svn_get_repocache_hash_without_subdir(self):
        scm_object = svn(self.cli, self.tasks)
        scm_object.url = 'https://github.com/openSUSE/obs-service-tar_scm.git'
        repohash = scm_object.get_repocache_hash('')
        self.assertEqual(
            repohash,
            'd5a57bc8ad6a3ecbca514a1a6fb48e2c9ee183ceb5f7d42e9fd5836918bd540c')

    def test_svn_get_repocache_hash_with_subdir(self):
        '''
        This test case proves that subdir is ignored in
        TarSCM.base.scm.get_repocache_hash
        '''
        scm_object = svn(self.cli, self.tasks)
        scm_object.url = 'https://github.com/openSUSE/obs-service-tar_scm.git'
        repohash = scm_object.get_repocache_hash('subdir')
        self.assertEqual(
            repohash,
            'b9761648b96f105d82a97b8a81f1ca060b015a3f882ef9a55ae6b5bf7be0d48a')

    def test_obscpio_create_archive(self):
        tc_name              = inspect.stack()[0][3]
        cl_name              = self.__class__.__name__
        scm_object           = git(self.cli, self.tasks)
        scm_object.clone_dir = os.path.join(self.fixtures_dir, tc_name, 'repo')
        ver                  = '0.1.1'
        scm_object.arch_dir  = os.path.join(self.fixtures_dir, tc_name, 'repo')
        outdir               = os.path.join(self.tmp_dir, cl_name, tc_name,
                                            'out')
        self.cli.outdir      = outdir
        arch                 = obscpio()
        os.makedirs(outdir)
        arch.create_archive(
            scm_object,
            cli      = self.cli,
            basename = 'test',
            dstname  = 'test',
            version  = '0.1.1'
        )

    def test_obscpio_extract_from_archive_one_file(self):
        tc_name = inspect.stack()[0][3]
        cl_name = self.__class__.__name__

        repodir = os.path.join(self.fixtures_dir, tc_name, 'repo')
        files   = ["test.spec"]
        outdir  = os.path.join(self.tmp_dir, cl_name, tc_name, 'out')
        arch    = obscpio()
        os.makedirs(outdir)
        arch.extract_from_archive(repodir, files, outdir)
        for fn in files:
            self.assertTrue(os.path.exists(os.path.join(outdir, fn)))

    def test_obscpio_extract_from_archive_multiple_files(self):
        tc_name = inspect.stack()[0][3]
        cl_name = self.__class__.__name__

        repodir = os.path.join(self.fixtures_dir, tc_name, 'repo')
        files   = ["test.spec", 'Readme.md']
        outdir  = os.path.join(self.tmp_dir, cl_name, tc_name, 'out')
        arch    = obscpio()
        os.makedirs(outdir)
        arch.extract_from_archive(repodir, files, outdir)
        for fn in files:
            self.assertTrue(os.path.exists(os.path.join(outdir, fn)))

    def test_obscpio_extract_from_archive_non_existing_file(self):
        tc_name = inspect.stack()[0][3]
        cl_name = self.__class__.__name__

        repodir = os.path.join(self.fixtures_dir, tc_name, 'repo')
        files   = ['nonexistantfile']
        outdir  = os.path.join(self.tmp_dir, cl_name, tc_name, 'out')
        arch    = obscpio()
        os.makedirs(outdir)
        self.assertRaisesRegexp(
            SystemExit,
            re.compile('No such file or directory'),
            arch.extract_from_archive,
            repodir,
            files,
            outdir
        )

    def test_obscpio_extract_from_archive_directory(self):
        tc_name = inspect.stack()[0][3]
        cl_name = self.__class__.__name__

        repodir = os.path.join(self.fixtures_dir, tc_name, 'repo')
        files   = ['dir1']
        outdir  = os.path.join(self.tmp_dir, cl_name, tc_name, 'out')
        arch    = TarSCM.archive.obscpio()
        os.makedirs(outdir)
        self.assertRaisesRegexp(
            IOError,
            re.compile('Is a directory:'),
            arch.extract_from_archive,
            repodir,
            files,
            outdir
        )

    def test_scm_tar(self):
        # TODO: This test case relies on the results of an other
        #       tests case. It has to be discussed if this is acceptable.
        tc_name    = inspect.stack()[0][3]
        cl_name    = self.__class__.__name__
        cur_cwd    = os.getcwd()
        scm_object = TarSCM.scm.tar(self.cli, self.tasks)
        wd         = os.path.join(self.tmp_dir, cl_name, tc_name)
        os.makedirs(os.path.join(wd, 'test'))
        info = os.path.join(wd, "test.obsinfo")
        print("INFOFILE: '%s'" % info)
        fh = open(info, 'w')
        fh.write(
            "name: test\n" +
            "version: 0.1.1\n" +
            "mtime: 1476683264\n" +
            "commit: fea6eb5f43841d57424843c591b6c8791367a9e5\n"
        )
        fh.close()
        os.chdir(wd)
        scm_object.fetch_upstream()
        # just to make coverage happy
        scm_object.update_cache()
        ts      = scm_object.get_timestamp()
        ver     = scm_object.detect_version(self.cli)
        empty   = scm_object.read_from_obsinfo(info, "nonexistantkey")

        self.assertTrue(os.path.isdir(os.path.join(wd, "test-0.1.1")))
        self.assertFalse(os.path.isdir(os.path.join(wd, "test")))
        self.assertEqual(ts, 1476683264)
        self.assertEqual(ver, "0.1.1")
        self.assertEqual(empty, "")
        # testing non existant basename
        fh = open(info, 'w')
        fh.write(
            "name: nonexistantbase\n" +
            "version: 0.1.1\n" +
            "mtime: 1476683264\n" +
            "commit: fea6eb5f43841d57424843c591b6c8791367a9e5\n"
        )
        fh.close()

        self.assertRaisesRegexp(
            SystemExit,
            re.compile('Error while moving from '),
            scm_object.fetch_upstream
        )

        # testing with no info
        os.chdir(cur_cwd)
        scm_object.args.obsinfo = None
        self.assertRaisesRegexp(
            SystemExit,
            re.compile('ERROR: no .obsinfo file found in directory:'),
            scm_object.fetch_upstream
        )
