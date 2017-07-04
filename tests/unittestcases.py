#!/usr/bin/env python2
from __future__ import print_function

import sys
import os
import re
import inspect
import copy
from mock import patch

import TarSCM

from TarSCM.helpers import Helpers
from TarSCM.config  import Config
from TarSCM.changes import Changes
from TarSCM.scm.git import Git
from TarSCM.scm.svn import Svn

if sys.version_info < (2, 7):
    # pylint: disable=import-error
    import unittest2 as unittest
else:
    import unittest


# pylint: disable=duplicate-code
class UnitTestCases(unittest.TestCase):
    def setUp(self):
        self.cli            = TarSCM.Cli()
        self.tasks          = TarSCM.Tasks(self.cli)
        self.tests_dir      = os.path.abspath(os.path.dirname(__file__))
        self.tmp_dir        = os.path.join(self.tests_dir, 'tmp')
        self.fixtures_dir   = os.path.join(self.tests_dir, 'fixtures',
                                           self.__class__.__name__)

        self.cli.parse_args(['--outdir', '.'])
        os.environ['CACHEDIRECTORY'] = ''

    def test_calc_dir_to_clone_to(self):

        clone_dirs = [
            '/local/repo.git',
            '/local/repo/.git',
            '/local/repo/.git/',
            'http://remote/repo.git;param?query#fragment',
            'http://remote/repo/.git;param?query#fragment',
        ]

        scm = Git(self.cli, self.tasks)

        for cdir in clone_dirs:
            scm.url = cdir
            scm._calc_dir_to_clone_to("")  # pylint: disable=protected-access
            self.assertTrue(scm.clone_dir.endswith('/repo'))
            self.tasks.cleanup()

    @patch('TarSCM.Helpers.safe_run')
    def test__git_log_cmd_with_args(self, safe_run_mock):
        scm     = Git(self.cli, self.tasks)
        # pylint: disable=unused-variable,protected-access
        new_cmd = scm._log_cmd(['-n1'], '')  # noqa
        safe_run_mock.assert_called_once_with(['git', 'log', '-n1'], cwd=None)

    @patch('TarSCM.Helpers.safe_run')
    def test__git_log_cmd_without_args(self, safe_run_mock):
        scm     = Git(self.cli, self.tasks)
        # pylint: disable=unused-variable,protected-access
        new_cmd = scm._log_cmd([], '')  # noqa
        safe_run_mock.assert_called_once_with(['git', 'log'], cwd=None)

    @patch('TarSCM.Helpers.safe_run')
    def test__git_log_cmd_with_subdir(self, safe_run_mock):
        scm     = Git(self.cli, self.tasks)
        # pylint: disable=unused-variable,protected-access
        new_cmd = scm._log_cmd(['-n1'], 'subdir')  # noqa
        safe_run_mock.assert_called_once_with(['git', 'log', '-n1',
                                               '--', 'subdir'], cwd=None)

    def test_safe_run_exception(self):
        helpers = Helpers()
        self.assertRaisesRegexp(
            SystemExit,
            re.compile(r"Command failed\(1\): ''"),
            helpers.safe_run,
            "/bin/false",
            cwd=None,
        )

    def test_config_files_ordering(self):
        tc_name = inspect.stack()[0][3]
        files = [
            [os.path.join(self.fixtures_dir, tc_name, 'a.cfg'), True],
            [os.path.join(self.fixtures_dir, tc_name, 'b.cfg'), True],
        ]
        var = Config(files).get(None, 'var')
        self.assertEqual(var, 'b')

    def test_config_no_faked_header(self):
        tc_name = inspect.stack()[0][3]
        files   = [
            [os.path.join(self.fixtures_dir, tc_name, 'test.ini'), False]
        ]
        var     = Config(files).get('general', 'apiurl')
        self.assertEqual(var, 'http://api.example.com')
        var     = Config(files).get(var, 'email')
        self.assertEqual(var, 'devel@example.com')

    def test_config_debug_tar_scm(self):
        tc_name = inspect.stack()[0][3]

        try:
            tmp = os.environ['DEBUG_TAR_SCM']
        except KeyError:
            tmp = None

        os.environ['DEBUG_TAR_SCM'] = "1"

        files = [[os.path.join(self.fixtures_dir, tc_name, 'test.rc'), True]]
        var = Config(files).get(None, 'var')
        self.assertEqual(var, None)

        if tmp:
            os.environ['DEBUG_TAR_SCM'] = tmp
        else:
            os.environ['DEBUG_TAR_SCM'] = ''
            os.unsetenv('DEBUG_TAR_SCM')

    def test_changes_get_chga_args(self):
        '''Test if getting changesauthor from cli args works'''
        chg                 = Changes()
        cli                 = copy.copy(self.cli)
        cli.changesauthor   = 'args@example.com'
        author              = chg.get_changesauthor(cli)
        self.assertEqual(author, 'args@example.com')

    def test_changes_get_chga_oscrc(self):
        '''Test if getting changesauthor from .oscrc works'''
        tc_name             = inspect.stack()[0][3]
        home                = os.environ['HOME']
        os.environ['HOME']  = os.path.join(self.fixtures_dir, tc_name)
        chg                 = Changes()
        author              = chg.get_changesauthor(self.cli)
        os.environ['HOME']  = home
        self.assertEqual(author, 'devel@example.com')

    def test_changes_get_chga_default(self):
        '''Test if getting changesauthor from .oscrc'''
        home                = os.environ['HOME']
        os.environ['HOME']  = '/nir/va/na'
        chg                 = Changes()
        author              = chg.get_changesauthor(self.cli)
        os.environ['HOME']  = home
        self.assertEqual(author, 'opensuse-packaging@opensuse.org')

    def test_changes_get_chga_home_rc(self):
        '''Test if getting changesauthor from rcfile in home dir'''
        home                = os.environ['HOME']
        tc_name             = inspect.stack()[0][3]
        home                = os.environ['HOME']
        os.environ['HOME']  = os.path.join(self.fixtures_dir, tc_name)
        chg                 = Changes()
        author              = chg.get_changesauthor(self.cli)
        os.environ['HOME']  = home
        self.assertEqual(author, 'devel@example.com')

    def test_git_repoc_hash_wo_subdir(self):
        '''Test to get git repocache dir without subdir'''
        scm_object = Git(self.cli, self.tasks)
        scm_object.url = 'https://github.com/openSUSE/obs-service-tar_scm.git'
        repohash = scm_object.get_repocache_hash(None)
        self.assertEqual(
            repohash,
            'c0f3245498ad916e9ee404acfd7aa59e29d53b7a063a8609735c1284c67b2161')

    def test_git_repoc_hash_w_subdir(self):
        '''
        This test case proves that subdir is ignored in
        TarSCM.base.scm.get_repocache_hash
        '''
        scm_object = Git(self.cli, self.tasks)
        scm_object.url = 'https://github.com/openSUSE/obs-service-tar_scm.git'
        repohash = scm_object.get_repocache_hash('subdir')
        self.assertEqual(
            repohash,
            'c0f3245498ad916e9ee404acfd7aa59e29d53b7a063a8609735c1284c67b2161')

    def test_svn_repoc_hash_wo_subdir(self):
        '''Test to get svn repocache dir without subdir'''
        scm_object = Svn(self.cli, self.tasks)
        scm_object.url = 'https://github.com/openSUSE/obs-service-tar_scm.git'
        repohash = scm_object.get_repocache_hash('')
        self.assertEqual(
            repohash,
            'd5a57bc8ad6a3ecbca514a1a6fb48e2c9ee183ceb5f7d42e9fd5836918bd540c')

    def test_svn_repoc_hash_w_subdir(self):
        '''
        This test case proves that subdir is ignored in
        TarSCM.base.scm.get_repocache_hash
        '''
        scm_object = Svn(self.cli, self.tasks)
        scm_object.url = 'https://github.com/openSUSE/obs-service-tar_scm.git'
        repohash = scm_object.get_repocache_hash('subdir')
        self.assertEqual(
            repohash,
            'b9761648b96f105d82a97b8a81f1ca060b015a3f882ef9a55ae6b5bf7be0d48a')

    @unittest.skip("Broken test, relies on the results of an other test case")
    def test_scm_tar(self):
        tc_name    = inspect.stack()[0][3]
        cl_name    = self.__class__.__name__
        cur_cwd    = os.getcwd()
        scm_object = TarSCM.scm.Tar(self.cli, self.tasks)
        wdir       = os.path.join(self.tmp_dir, cl_name, tc_name)
        os.makedirs(os.path.join(wdir, 'test'))
        info = os.path.join(wdir, "test.obsinfo")
        print("INFOFILE: '%s'" % info)
        f_h = open(info, 'w')
        f_h.write(
            "name: test\n" +
            "version: 0.1.1\n" +
            "mtime: 1476683264\n" +
            "commit: fea6eb5f43841d57424843c591b6c8791367a9e5\n"
        )
        f_h.close()
        os.chdir(wdir)
        scm_object.fetch_upstream()
        # just to make coverage happy
        scm_object.update_cache()
        tstamp  = scm_object.get_timestamp()
        ver     = scm_object.detect_version(self.cli)
        empty   = scm_object.read_from_obsinfo(info, "nonexistantkey")

        self.assertTrue(os.path.isdir(os.path.join(wdir, "test-0.1.1")))
        self.assertFalse(os.path.isdir(os.path.join(wdir, "test")))
        self.assertEqual(tstamp, 1476683264)
        self.assertEqual(ver, "0.1.1")
        self.assertEqual(empty, "")
        # testing non existant basename
        f_h = open(info, 'w')
        f_h.write(
            "name: nonexistantbase\n" +
            "version: 0.1.1\n" +
            "mtime: 1476683264\n" +
            "commit: fea6eb5f43841d57424843c591b6c8791367a9e5\n"
        )
        f_h.close()

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
