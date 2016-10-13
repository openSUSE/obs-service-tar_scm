#!/usr/bin/env python2

import unittest
import sys
import os
import re
from mock import patch

import TarSCM
import argparse

from TarSCM.helpers import helpers

class UnitTestCases(unittest.TestCase):
    def setUp(self):
        self.cli        = TarSCM.cli()
        self.tasks      = TarSCM.tasks()
        self.tests_dir  = os.path.abspath(os.path.dirname(__file__))  # os.getcwd()
        self.tmp_dir    = os.path.join(self.tests_dir, 'tmp')

        self.cli.parse_args(['--outdir','.'])
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

        scm     = TarSCM.scm.git(self.cli,self.tasks)

        for cd in clone_dirs:
            scm.url=cd
            scm._calc_dir_to_clone_to("")
            self.assertEqual(scm.clone_dir, os.path.join(scm.repodir, 'repo'))

    @patch('TarSCM.helpers.safe_run')
    def test__git_log_cmd_with_args(self, safe_run_mock):
        scm     = TarSCM.scm.git(self.cli,self.tasks)
        new_cmd = scm._log_cmd(['-n1'],'')
        safe_run_mock.assert_called_once_with(['git', 'log', '-n1'], cwd=None)

    @patch('TarSCM.helpers.safe_run')
    def test__git_log_cmd_without_args(self, safe_run_mock):
        scm     = TarSCM.scm.git(self.cli,self.tasks)
        new_cmd = scm._log_cmd([], '')
        safe_run_mock.assert_called_once_with(['git', 'log'], cwd=None)

    @patch('TarSCM.helpers.safe_run')
    def test__git_log_cmd_with_subdir(self, safe_run_mock):
        scm     = TarSCM.scm.git(self.cli,self.tasks)
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
