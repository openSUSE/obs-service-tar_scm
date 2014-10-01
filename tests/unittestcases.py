#!/usr/bin/python

import unittest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))
from tar_scm import _calc_dir_to_clone_to

class UnitTestCases(unittest.TestCase):

    def test_calc_dir_to_clone_to(self):
        scm = 'git'
        outdir = '/out/'

        clone_dir = _calc_dir_to_clone_to(scm, '/local/repo.git', outdir)
        self.assertEqual(clone_dir, os.path.join(outdir, 'repo'))

        clone_dir = _calc_dir_to_clone_to(scm, '/local/repo/.git', outdir)
        self.assertEqual(clone_dir, os.path.join(outdir, 'repo'))

        clone_dir = _calc_dir_to_clone_to(scm, '/local/repo/.git/', outdir)
        self.assertEqual(clone_dir, os.path.join(outdir, 'repo'))

        clone_dir = _calc_dir_to_clone_to(scm, 'http://remote/repo.git;param?query#fragment', outdir)
        self.assertEqual(clone_dir, os.path.join(outdir, 'repo'))

        clone_dir = _calc_dir_to_clone_to(scm, 'http://remote/repo/.git;param?query#fragment', outdir)
        self.assertEqual(clone_dir, os.path.join(outdir, 'repo'))
