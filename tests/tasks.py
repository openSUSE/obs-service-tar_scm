import unittest
import sys
import os
import argparse
import inspect
import re
import copy
import shutil
from mock import MagicMock

from tar_scm import TarSCM


class TasksTestCases(unittest.TestCase):
    def setUp(self):
        self.basedir        = os.path.abspath(os.path.dirname(__file__))
        self.tests_dir      = os.path.abspath(os.path.dirname(__file__))  # os.getcwd()
        self.tmp_dir        = os.path.join(self.tests_dir, 'tmp')
        self.outdir         = os.path.join(self.tmp_dir, self.__class__.__name__, 'out')
        self._prepare_cli()

    def tearDown(self):
        if os.path.exists(self.outdir):
            shutil.rmtree(self.outdir)

    def _prepare_cli(self):
        self.cli = TarSCM.cli()
        if not os.path.exists(self.outdir):
            os.makedirs(self.outdir)
        self.cli.parse_args(['--outdir',self.outdir,'--scm','git'])
        self.cli.snapcraft  = True

    def _cd_fixtures_dir(self):
        self.cur_dir = os.getcwd()
        cl_name = self.__class__.__name__
        fn_name = inspect.stack()[1][3]
        try:
            os.chdir(os.path.join(self.basedir,'fixtures', cl_name, fn_name))
        except(OSError) as e:
            print ( "current working directory: %s" % os.getcwd() )
            raise(e)

    def _restore_cwd(self):
        try:
            os.chdir(self.basedir)
        except(OSError) as e:
            print ( "failed to restore : current working directory: %s" % os.getcwd() )
            raise(e)

    def test_generate_task_list_single_task(self):
        expected = {'scm': 'bzr', 'clone_prefix': '_obs_', 'snapcraft': True,
                'revision': None, 'url': 'lp:~mterry/libpipeline/printf',
                'filename': 'libpipeline', 'use_obs_scm': True,
                'jailed': 0, 'outdir': self.cli.outdir,'changesgenerate': False}
        self._cd_fixtures_dir()
        tasks           = TarSCM.tasks()
        tasks.generate_list(self.cli)
        self._restore_cwd()
        for k in expected.keys():
            self.assertEqual(tasks.task_list[0].__dict__[k],expected[k])
        self.assertEqual(len(tasks.task_list),1)
        
    def test_generate_task_list_multi_tasks(self):
        expected        = {
            'libpipeline' : {
                'changesgenerate': False,
                'clone_prefix': '_obs_',
                'filename': 'libpipeline',
                'jailed': 0,
                'outdir': self.cli.outdir,
                'revision': None,
                'scm': 'bzr',
                'snapcraft': True,
                'url': 'lp:~mterry/libpipeline/printf',
                'use_obs_scm': True
            },
            'kanku' : {
                'changesgenerate': False,
                'clone_prefix': '_obs_',
                'filename': 'kanku',
                'jailed': 0,
                'outdir': self.cli.outdir,
                'revision': None,
                'scm': 'git',
                'snapcraft': True,
                'url': 'git@github.com:M0ses/kanku',
                'use_obs_scm': True
            },
        }
        self._cd_fixtures_dir()
        tasks           = TarSCM.tasks()
        tasks.generate_list(self.cli)
        # test values in the objects instead of objects
        for got in tasks.task_list:
            gf = got.__dict__['filename']
            for k in expected[gf].keys():
                self.assertEqual(got.__dict__[k],expected[gf][k])
        self._restore_cwd()

    def test_tasks_finalize(self):
        expected = '''apps:
  pipelinetest:
    command: ./bin/test
description: 'This is an example package of an autotools project built with snapcraft

  using a remote source.

  '
name: pipelinetest
parts:
  kanku:
    after:
    - libpipeline
    plugin: make
    source: kanku
  libpipeline:
    plugin: autotools
    source: libpipeline
summary: Libpipeline example
version: 1.0
'''
        self._cd_fixtures_dir()
        tasks           = TarSCM.tasks()
        if not os.path.exists(self.cli.outdir):
            os.makedirs(self.cli.outdir)
        tasks.generate_list(self.cli)
        tasks.finalize(self.cli)
        i = 0
        self._restore_cwd()
        sf  = open(os.path.join(self.cli.outdir,'_service:snapcraft:snapcraft.yaml'),'r')
        got = sf.read()
        sf.close()
        self.assertEqual(got,expected)

    def test_cleanup(self):
        tasks           = TarSCM.tasks()
        if not os.path.exists(self.tmp_dir):
            os.mkdir(self.tmp_dir)
        if not os.path.exists(os.path.join(self.tmp_dir,self.__class__.__name__)):
            os.mkdir(os.path.join(self.tmp_dir,self.__class__.__name__))
        os.mkdir(os.path.join(self.tmp_dir,self.__class__.__name__,'test1'))
        tasks.cleanup_dirs.append(os.path.join(self.tmp_dir,self.__class__.__name__,'test1'))
        tasks.cleanup_dirs.append(os.path.join(self.tmp_dir,self.__class__.__name__,'does not exits'))
        tasks.cleanup_dirs.append(os.path.join(self.tmp_dir,self.__class__.__name__))
        tasks.cleanup()
        self.assertEqual(os.path.exists(os.path.join(self.tmp_dir,self.__class__.__name__)),False)

    def test_get_version(self):
        class FakeSCM():
            def detect_version(self, args):
                return '0.0.1'

        scm     = FakeSCM()
        tasks   = TarSCM.tasks()
        v       = tasks.get_version(scm, self.cli)
        self.assertEqual(v,'0.0.1')
        self.cli.versionprefix = "r"
        v       = tasks.get_version(scm, self.cli)
        self.assertEqual(v,'r.0.0.1')

    def test_process_list(self):
        tasks   = TarSCM.tasks()
        self.cli.snapcraft = False
        tasks._process_single_task = MagicMock(name='_process_single_task')
        tasks.generate_list(self.cli)
        tasks.process_list()
