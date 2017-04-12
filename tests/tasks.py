import unittest
import os
import inspect
import re
import shutil
from mock import MagicMock

from tar_scm import TarSCM


class TasksTestCases(unittest.TestCase):
    def setUp(self):
        self.basedir        = os.path.abspath(os.path.dirname(__file__))
        self.tests_dir      = os.path.abspath(os.path.dirname(__file__))
        self.tmp_dir        = os.path.join(self.tests_dir, 'tmp')
        self.class_name = self.__class__.__name__
        self.outdir         = os.path.join(self.tmp_dir, self.class_name, 'out')
        self._prepare_cli()

    def tearDown(self):
        if os.path.exists(self.outdir):
            shutil.rmtree(self.outdir)

    def _prepare_cli(self):
        self.cli = TarSCM.cli()
        if not os.path.exists(self.outdir):
            os.makedirs(self.outdir)
        self.cli.parse_args(['--outdir', self.outdir, '--scm', 'git'])
        self.cli.snapcraft  = True

    def _cd_fixtures_dir(self):
        self.cur_dir = os.getcwd()
        cl_name = self.class_name
        fn_name = inspect.stack()[1][3]
        try:
            os.chdir(os.path.join(self.basedir, 'fixtures', cl_name, fn_name))
        except(OSError) as e:
            print "current working directory: %s" % os.getcwd()
            raise(e)

    def _restore_cwd(self):
        try:
            os.chdir(self.basedir)
        except(OSError) as e:
            print("failed to restore : current working directory: %s"
                  % os.getcwd())
            raise(e)

    def test_generate_task_list_single_task(self):
        expected = {'scm': 'bzr', 'clone_prefix': '_obs_', 'snapcraft': True,
                    'revision': None, 'url': 'lp:~mterry/libpipeline/printf',
                    'filename': 'libpipeline', 'use_obs_scm': True,
                    'outdir': self.cli.outdir, 'changesgenerate': False}
        self._cd_fixtures_dir()
        tasks           = TarSCM.tasks()
        tasks.generate_list(self.cli)
        self._restore_cwd()
        for k in expected.keys():
            self.assertEqual(tasks.task_list[0].__dict__[k], expected[k])
        self.assertEqual(len(tasks.task_list), 1)

    def test_generate_task_list_multi_tasks(self):
        expected        = [
            {
                'changesgenerate': False,
                'clone_prefix': '_obs_',
                'filename': 'libpipeline',
                'outdir': self.cli.outdir,
                'revision': None,
                'scm': 'bzr',
                'snapcraft': True,
                'url': 'lp:~mterry/libpipeline/printf',
                'use_obs_scm': True
            },
            {
                'changesgenerate': False,
                'clone_prefix': '_obs_',
                'filename': 'kanku',
                'outdir': self.cli.outdir,
                'revision': None,
                'scm': 'git',
                'snapcraft': True,
                'url': 'git@github.com:M0ses/kanku',
                'use_obs_scm': True
            },
        ]
        self._cd_fixtures_dir()
        tasks           = TarSCM.tasks()
        tasks.generate_list(self.cli)
        i = 0
        # test values in the objects instead of objects
        for got in tasks.task_list:
            for k in expected[i].keys():
                self.assertEqual(got.__dict__[k], expected[i][k])
            i += 1
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
        sf  = open(os.path.join(self.cli.outdir,
                                '_service:snapcraft:snapcraft.yaml'), 'r')
        got = sf.read()
        sf.close()
        self.assertEqual(got, expected)

    def test_cleanup(self):
        tasks           = TarSCM.tasks()
        path = os.path.join(self.tmp_dir, self.class_name)
        if not os.path.exists(self.tmp_dir):
            os.mkdir(self.tmp_dir)
        if not os.path.exists(path):
            os.mkdir(path)
        os.mkdir(os.path.join(path, 'test1'))
        tasks.cleanup_dirs.append(os.path.join(path, 'test1'))
        tasks.cleanup_dirs.append(os.path.join(path, 'does not exits'))
        tasks.cleanup_dirs.append(path)
        tasks.cleanup()
        self.assertEqual(os.path.exists(path), False)

    def test_prep_tree_for_archive(self):
        tasks   = TarSCM.tasks()
        basedir  = os.path.join(self.tmp_dir, self.class_name)
        dir1    = os.path.join(basedir, "test1")
        os.makedirs(dir1)
        self.assertRaisesRegexp(
            Exception,
            re.compile('src and dst refer to same file'),
            tasks.prep_tree_for_archive,
            basedir,
            "test1",
            basedir,
            "test1"
        )

        self.assertRaisesRegexp(
            Exception,
            re.compile('No such file or directory'),
            tasks.prep_tree_for_archive,
            basedir,
            "test2",
            basedir,
            "test1"
        )

        self.assertEqual(
            tasks.prep_tree_for_archive(basedir, "test1", basedir, "test2"),
            os.path.join(basedir, "test2")
        )

    def test_get_version(self):
        class FakeSCM():
            def detect_version(self, args, repodir):
                return '0.0.1'

        scm     = FakeSCM()
        tasks   = TarSCM.tasks()
        v       = tasks.get_version(scm, self.cli, '')
        self.assertEqual(v, '0.0.1')
        self.cli.versionprefix = "r"
        v       = tasks.get_version(scm, self.cli, '')
        self.assertEqual(v, 'r.0.0.1')

    def test_process_list(self):
        tasks   = TarSCM.tasks()
        self.cli.snapcraft = False
        tasks._process_single_task = MagicMock(name='_process_single_task')
        tasks.generate_list(self.cli)
        tasks.process_list()
