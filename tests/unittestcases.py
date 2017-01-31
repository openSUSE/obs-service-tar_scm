#!/usr/bin/env python2

import unittest
import sys
import os
from mock import patch

from tar_scm import TarSCM
import argparse

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

        cli = TarSCM.cli()
        scm = TarSCM.git(cli)

        for cd in clone_dirs:
            scm.url=cd
            clone_dir = scm._calc_dir_to_clone_to("")
            self.assertEqual(clone_dir, os.path.join(scm.repodir, 'repo'))

    @patch('tar_scm.TarSCM.helpers.safe_run')
    def test__git_log_cmd_with_args(self, safe_run_mock):
        cli = TarSCM.cli()
        scm = TarSCM.git(cli)
        new_cmd = scm._log_cmd(['-n1'], None, '')
        safe_run_mock.assert_called_once_with(['git', 'log', '-n1'], cwd=None)

    @patch('tar_scm.TarSCM.helpers.safe_run')
    def test__git_log_cmd_without_args(self, safe_run_mock):
        cli = TarSCM.cli()
        scm = TarSCM.git(cli)
        new_cmd = scm._log_cmd([], None, '')
        safe_run_mock.assert_called_once_with(['git', 'log'], cwd=None)

    @patch('tar_scm.TarSCM.helpers.safe_run')
    def test__git_log_cmd_with_subdir(self, safe_run_mock):
        cli = TarSCM.cli()
        scm = TarSCM.git(cli)
        new_cmd = scm._log_cmd(['-n1'], None, 'subdir')
        safe_run_mock.assert_called_once_with(['git', 'log', '-n1',
                                               '--', 'subdir'], cwd=None)
