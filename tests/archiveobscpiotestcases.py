#!/usr/bin/env python2
from __future__ import print_function

import sys
import os
import re
import inspect

import TarSCM

from TarSCM.scm.git import Git
from TarSCM.archive import ObsCpio

if sys.version_info < (2, 7):
    # pylint: disable=import-error
    import unittest2 as unittest
else:
    import unittest


class ArchiveOBSCpioTestCases(unittest.TestCase):
    def setUp(self):
        self.cli            = TarSCM.Cli()
        self.tasks          = TarSCM.Tasks(self.cli)
        self.tests_dir      = os.path.abspath(os.path.dirname(__file__))
        self.tmp_dir        = os.path.join(self.tests_dir, 'tmp')
        self.fixtures_dir   = os.path.join(self.tests_dir, 'fixtures',
                                           self.__class__.__name__)

        self.cli.parse_args(['--outdir', '.'])
        os.environ['CACHEDIRECTORY'] = ''

    @unittest.skip("Broken test, relies on a fixture set which is a .git file"
                   " which is excluded while package building")
    def test_obscpio_create_archive(self):
        tc_name              = inspect.stack()[0][3]
        cl_name              = self.__class__.__name__
        scm_object           = Git(self.cli, self.tasks)
        scm_object.clone_dir = os.path.join(self.fixtures_dir, tc_name, 'repo')
        scm_object.arch_dir  = os.path.join(self.fixtures_dir, tc_name, 'repo')
        outdir               = os.path.join(self.tmp_dir, cl_name, tc_name,
                                            'out')
        self.cli.outdir      = outdir
        arch                 = ObsCpio()
        os.makedirs(outdir)
        arch.create_archive(
            scm_object,
            cli      = self.cli,
            basename = 'test',
            dstname  = 'test',
            version  = '0.1.1'
        )

    def test_obscpio_extract_of(self):
        '''
        Test obscpio to extract one file from archive
        '''
        tc_name = inspect.stack()[0][3]
        cl_name = self.__class__.__name__

        repodir = os.path.join(self.fixtures_dir, tc_name, 'repo')
        files   = ["test.spec"]
        outdir  = os.path.join(self.tmp_dir, cl_name, tc_name, 'out')
        arch    = ObsCpio()
        os.makedirs(outdir)
        arch.extract_from_archive(repodir, files, outdir)
        for fname in files:
            self.assertTrue(os.path.exists(
                os.path.join(outdir, fname)))

    def test_obscpio_extract_mf(self):
        '''
        Test obscpio to extract multiple files from archive
        '''
        tc_name = inspect.stack()[0][3]
        cl_name = self.__class__.__name__

        repodir = os.path.join(self.fixtures_dir, tc_name, 'repo')
        files   = ["test.spec", 'Readme.md']
        outdir  = os.path.join(self.tmp_dir, cl_name, tc_name, 'out')
        arch    = ObsCpio()
        os.makedirs(outdir)
        arch.extract_from_archive(repodir, files, outdir)
        for fname in files:
            self.assertTrue(os.path.exists(
                os.path.join(outdir, fname)))

    def test_obscpio_extract_nef(self):
        '''
        Test obscpio to extract non existant file from archive
        '''
        tc_name = inspect.stack()[0][3]
        cl_name = self.__class__.__name__

        repodir = os.path.join(self.fixtures_dir, tc_name, 'repo')
        files   = ['nonexistantfile']
        outdir  = os.path.join(self.tmp_dir, cl_name, tc_name, 'out')
        arch    = ObsCpio()
        os.makedirs(outdir)
        self.assertRaisesRegexp(
            SystemExit,
            re.compile('No such file or directory'),
            arch.extract_from_archive,
            repodir,
            files,
            outdir
        )

    @unittest.skip("Broken test, actually raises "
                   "SystemExit: No such file or directory")
    def test_obscpio_extract_d(self):
        '''
        Test obscpio to extract directory from archive
        '''
        tc_name = inspect.stack()[0][3]
        cl_name = self.__class__.__name__

        repodir = os.path.join(self.fixtures_dir, tc_name, 'repo')
        files   = ['dir1']
        outdir  = os.path.join(self.tmp_dir, cl_name, tc_name, 'out')
        arch    = TarSCM.archive.ObsCpio()
        os.makedirs(outdir)
        self.assertRaisesRegexp(
            IOError,
            re.compile('Is a directory:'),
            arch.extract_from_archive,
            repodir,
            files,
            outdir
        )
