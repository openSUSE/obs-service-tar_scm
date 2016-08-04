#!/usr/bin/env python2

import unittest
import sys
import os
from mock import patch

from tar_scm import _calc_dir_to_clone_to
from tar_scm import _git_log_cmd
from tar_scm import is_proxy_defined
from tar_scm import define_global_scm_command


class UnitTestCases(unittest.TestCase):

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

        for cd in clone_dirs:
            clone_dir = _calc_dir_to_clone_to(scm, cd, "", outdir)
            self.assertEqual(clone_dir, os.path.join(outdir, 'repo'))

    @patch('tar_scm.safe_run')
    def test__git_log_cmd_with_args(self, safe_run_mock):
        global_scm_command = define_global_scm_command('git')
        new_cmd = _git_log_cmd(['-n1'], None, '')
        safe_run_mock.assert_called_once_with(global_scm_command +
                                              ['log', '-n1'], cwd=None)

    @patch('tar_scm.safe_run')
    def test__git_log_cmd_without_args(self, safe_run_mock):
        global_scm_command = define_global_scm_command('git')
        new_cmd = _git_log_cmd([], None, '')
        safe_run_mock.assert_called_once_with(global_scm_command +
                                              ['log'], cwd=None)

    @patch('tar_scm.safe_run')
    def test__git_log_cmd_with_subdir(self, safe_run_mock):
        global_scm_command = define_global_scm_command('git')
        new_cmd = _git_log_cmd(['-n1'], None, 'subdir')
        safe_run_mock.assert_called_once_with(global_scm_command +
                                              ['log', '-n1', '--', 'subdir'],
                                              cwd=None)
