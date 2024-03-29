#!/usr/bin/env python
from __future__ import print_function

import os
import glob

from utils import file_write_legacy

from tests.tarfixtures    import TarFixtures
from tests.testenv        import TestEnvironment
from tests.testassertions import TestAssertions
from tests.fake_classes   import FakeCli, FakeTasks

from TarSCM.scm.tar       import Tar


class TarTestCases(TestEnvironment, TestAssertions):
    """Unit tests for 'tar'.

    tar-specific tests are in this class.  Other shared tests are
    included via the class inheritance hierarchy.
    """

    scm            = 'tar'
    fixtures_class = TarFixtures

    def test_tar_scm_finalize(self):
        wdir       = self.pkgdir
        info = os.path.join(wdir, "test.obsinfo")
        print("INFOFILE: '%s'" % info)
        os.chdir(self.pkgdir)
        out_str = "name: pkgname\n" \
                  "version: 0.1.1\n" \
                  "mtime: 1476683264\n" \
                  "commit: fea6eb5f43841d57424843c591b6c8791367a9e5\n"
        file_write_legacy(info, out_str)

        src_dir = os.path.join(wdir, "pkgname")
        os.mkdir(src_dir)
        self.tar_scm_std()
        self.assertTrue(os.path.isdir(src_dir))

    def test_tar_scm_no_finalize(self):  # pylint: disable=no-self-use
        cli                 = FakeCli()
        tasks               = FakeTasks()
        tar_obj             = Tar(cli, tasks)
        tar_obj.finalize()


    def test_tar_scm_multiple_obsinfo(self):
        wdir       = self.pkgdir
        info = os.path.join(wdir, "test1.obsinfo")
        print("INFOFILE: '%s'" % info)
        os.chdir(self.pkgdir)
        out_str = "name: pkgname1\n" \
                  "version: 0.1.1\n" \
                  "mtime: 1476683264\n" \
                  "commit: fea6eb5f43841d57424843c591b6c8791367a9e5\n"
        file_write_legacy(info, out_str)

        info = os.path.join(wdir, "test2.obsinfo")
        print("INFOFILE: '%s'" % info)
        os.chdir(self.pkgdir)
        out_str = "name: pkgname2\n" \
                  "version: 0.1.2\n" \
                  "mtime: 1476683264\n" \
                  "commit: fea6eb5f43841d57424843c591b6c8791367a9e5\n"
        file_write_legacy(info, out_str)

        src_dir = os.path.join(wdir, "pkgname1")
        os.mkdir(src_dir)
        src_dir = os.path.join(wdir, "pkgname2")
        os.mkdir(src_dir)
        self.tar_scm_std()
        self.assertTrue(os.path.isdir(src_dir))
        os.chdir(self.outdir)
        files = glob.glob('*.tar')
        files.sort()
        expected = ['pkgname1-0.1.1-0.1.1.tar', 'pkgname2-0.1.2-0.1.2.tar']
        self.assertEqual(files, expected)
