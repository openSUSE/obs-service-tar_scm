#!/usr/bin/env python2

import unittest
import sys
import os

from mock import patch

from tar_scm import TarSCM
import argparse
import inspect
#import

class SnapcraftTestCases(unittest.TestCase):
    def setUp(self):
        self.cli             = TarSCM.cli()
        self.cli.snapcraft   = True
        self.basedir         = os.path.abspath(os.path.dirname(__file__))

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
                'jailed': None, 'outdir': None}
        self._cd_fixtures_dir()
        tasks           = TarSCM.tasks()
        tasks.generate_list(self.cli)
        self._restore_cwd()

        self.assertEqual(tasks.task_list[0].__dict__,expected)
        self.assertEqual(len(tasks.task_list),1)
        
    def test_generate_task_list_multi_tasks(self):
        expected        = [
            {
                'clone_prefix': '_obs_',
                'filename': 'libpipeline',
                'jailed': None,
                'outdir': None,
                'revision': None,
                'scm': 'bzr',
                'snapcraft': True,
                'url': 'lp:~mterry/libpipeline/printf',
                'use_obs_scm': True
            },
            {
                'clone_prefix': '_obs_',
                'filename': 'kanku',
                'jailed': None,
                'outdir': None,
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
        for got in tasks.task_list:
            self.assertEqual(got.__dict__,expected[i])
            i += 1
        self._restore_cwd()
