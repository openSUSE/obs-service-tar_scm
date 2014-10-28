#!/usr/bin/env python2

import unittest
import sys
import os

here = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(here, '..'))

from tar_scm import _calc_dir_to_clone_to


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
            clone_dir = _calc_dir_to_clone_to(scm, cd, outdir)
            self.assertEqual(clone_dir, os.path.join(outdir, 'repo'))
