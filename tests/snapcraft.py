import sys
import os
import argparse
import inspect

from mock import patch

from tar_scm import TarSCM

if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

class SnapcraftTestCases(unittest.TestCase):
    def setUp(self):
        self.basedir        = os.path.abspath(os.path.dirname(__file__))
        self.cli            = TarSCM.cli()
        self.cli.outdir     = os.path.join(self.basedir,'tmp',self.__class__.__name__,'out')
        self.cli.snapcraft  = True

    def _cd_fixtures_dir(self):
        print "_cd_fixtures_dir"
        print "function: %s" % inspect.stack()[1][3]
        self.cur_dir = os.getcwd()
        cl_name = self.__class__.__name__
        fn_name = inspect.stack()[1][3]
        try:
            os.chdir(os.path.join(self.basedir,'fixtures', cl_name, fn_name))
        except(OSError) as e:
            print "current working directory: %s" % os.getcwd()
            raise(e)

    def _restore_cwd(self):
        try:
            os.chdir(self.basedir)
        except(OSError) as e:
            print "failed to restore : failed to restore : current working directory: %s" % os.getcwd()
            raise(e)

    def test_generate_task_list_single_task(self):
        expected = {'scm': 'bzr', 'clone_prefix': '_obs_', 'snapcraft': True,
                'revision': None, 'url': 'lp:~mterry/libpipeline/printf',
                'filename': 'libpipeline', 'use_obs_scm': True,
                'outdir': self.cli.outdir,'changesgenerate': False}
        self._cd_fixtures_dir()
        tasks           = TarSCM.tasks()
        tasks.generate_list(self.cli)
        self._restore_cwd()

        self.assertEqual(tasks.task_list[0].__dict__,expected)
        self.assertEqual(len(tasks.task_list),1)
        
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
            self.assertEqual(got.__dict__,expected[i])
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
        os.makedirs(self.cli.outdir)
        tasks.generate_list(self.cli)
        tasks.finalize(self.cli)
        i = 0
        self._restore_cwd()
	sf  = open(os.path.join(self.cli.outdir,'_service:snapcraft:snapcraft.yaml'),'r')
	got = sf.read()
	sf.close()
        self.assertEqual(got,expected)
