#!/usr/bin/env python2
from __future__ import print_function

import sys
import os
import re
import inspect
import tarfile
from mock import patch

import TarSCM

from TarSCM.archive import Tar

if sys.version_info < (2, 7):
    # pylint: disable=import-error
    import unittest2 as unittest
else:
    import unittest


class ArchiveTarTestCases(unittest.TestCase):
    def setUp(self):
        self.cli            = TarSCM.Cli()
        self.tasks          = TarSCM.Tasks(self.cli)
        self.tests_dir      = os.path.abspath(os.path.dirname(__file__))
        self.tmp_dir        = os.path.join(self.tests_dir, 'tmp')
        self.fixtures_dir   = os.path.join(self.tests_dir, 'fixtures',
                                           self.__class__.__name__)

        self.cli.parse_args(['--outdir', '.'])
        os.environ['CACHEDIRECTORY'] = ''

    @patch('TarSCM.scm.base')
    def test_tar_create_archive(self, mock_scm):
        tc_name              = inspect.stack()[0][3]
        cl_name              = self.__class__.__name__
        mock_scm.clone_dir = os.path.join(self.fixtures_dir, tc_name, 'repo')
        mock_scm.arch_dir  = os.path.join(self.fixtures_dir, tc_name, 'repo')
        outdir               = os.path.join(self.tmp_dir, cl_name, tc_name,
                                            'out')
        self.cli.outdir      = outdir
        arch                 = Tar()
        os.makedirs(outdir)
        arch.create_archive(
            mock_scm,
            cli      = self.cli,
            basename = 'test',
            dstname  = 'test',
            version  = '0.1.1'
        )
        outfile = os.sep.join([outdir, 'test.tar'])
        assert os.path.exists(outfile)
        with tarfile.open(outfile, 'r') as tar:
            assert tar.getmember('repo')
            assert tar.getmember('repo/dir1/.keep')

    @patch('TarSCM.scm.base')
    def test_tar_create_archive_no_topdir(self, mock_scm):
        tc_name              = inspect.stack()[0][3]
        cl_name              = self.__class__.__name__
        mock_scm.clone_dir = os.path.join(self.fixtures_dir, tc_name, 'repo')
        mock_scm.arch_dir  = os.path.join(self.fixtures_dir, tc_name, 'repo')
        outdir               = os.path.join(self.tmp_dir, cl_name, tc_name,
                                            'out')
        self.cli.outdir      = outdir
        arch                 = Tar()
        os.makedirs(outdir)
        self.cli.include_topdir = False
        arch.create_archive(
            mock_scm,
            cli      = self.cli,
            basename = 'test',
            dstname  = 'test',
            version  = '0.1.1'
        )
        outfile = os.sep.join([outdir, 'test.tar'])
        assert os.path.exists(outfile)
        with tarfile.open(outfile, 'r') as tar:
            assert tar.getmember('dir1/.keep')
