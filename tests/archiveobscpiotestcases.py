#!/usr/bin/env python2
from __future__ import print_function

import sys
import os
import re
import inspect
import shutil

import TarSCM

from TarSCM.scm.git import Git
from TarSCM.archive import ObsCpio

from tests.gitfixtures import GitFixtures
from tests.scmlogs import ScmInvocationLogs


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

    def test_obscpio_create_archive(self):
        tc_name              = inspect.stack()[0][3]
        cl_name              = self.__class__.__name__
        c_dir                = os.path.join(self.tmp_dir, tc_name)
        f_dir                = os.path.join(self.fixtures_dir, tc_name, 'repo')
        shutil.copytree(f_dir, c_dir)
        scmlogs              = ScmInvocationLogs('git', c_dir)
        scmlogs.next('start-test')
        fixture              = GitFixtures(c_dir, scmlogs)
        fixture.init()
        scm_object           = Git(self.cli, self.tasks)
        scm_object.clone_dir = fixture.repo_path
        scm_object.arch_dir  = fixture.repo_path
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

    def test_obscpio_broken_link(self):
        tc_name              = inspect.stack()[0][3]
        cl_name              = self.__class__.__name__
        c_dir                = os.path.join(self.tmp_dir, tc_name)
        scmlogs              = ScmInvocationLogs('git', c_dir)
        scmlogs.next('start-test')
        fixture              = GitFixtures(c_dir, scmlogs)
        fixture.init()
        scm_object           = Git(self.cli, self.tasks)
        scm_object.clone_dir = fixture.repo_path
        scm_object.arch_dir  = fixture.repo_path
        outdir               = os.path.join(self.tmp_dir, cl_name, tc_name,
                                            'out')
        cwd = os.getcwd()
        print("cwd = %s" % cwd)
        os.chdir(fixture.repo_path)
        os.symlink('non-existant-file', 'broken-link')
        fixture.run('add broken-link')
        fixture.run("commit -m 'added broken-link'")
        os.chdir(cwd)

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

    def test_extract_link_outside_repo(self):
        '''
        Test if a link outside the repo gets detected
        '''
        tc_name = inspect.stack()[0][3]
        cl_name = self.__class__.__name__
        files   = ['dir1/etc/passwd']

        # create repodir
        repodir = os.path.join(self.tmp_dir, tc_name, 'repo')
        os.makedirs(repodir)

        # create outdir
        outdir  = os.path.join(self.tmp_dir, cl_name, tc_name, 'out')
        os.makedirs(outdir)

        os.symlink("/", os.path.join(repodir, 'dir1'))
        arch    = TarSCM.archive.ObsCpio()
        self.assertRaisesRegexp(
            SystemExit,
            re.compile('tries to escape the repository'),
            arch.extract_from_archive,
            repodir,
            files,
            outdir
        )

    def test_obscpio_extract_glob(self):
        '''
        Test obscpio to extract file glob from archive
        '''
        tc_name = inspect.stack()[0][3]
        cl_name = self.__class__.__name__

        repodir = os.path.join(self.fixtures_dir, tc_name, 'repo')
        files   = ["test.*"]
        files_expected = ["test.spec", "test.rpmlintrc"]
        outdir  = os.path.join(self.tmp_dir, cl_name, tc_name, 'out')
        arch    = ObsCpio()
        os.makedirs(outdir)
        arch.extract_from_archive(repodir, files, outdir)
        for fname in files_expected:
            self.assertTrue(os.path.exists(
                os.path.join(outdir, fname)))
