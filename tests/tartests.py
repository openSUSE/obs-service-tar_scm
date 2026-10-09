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

    def test_tar_delete_obscpio(self):
        """Test that .obscpio is deleted when --delete is set."""
        wdir = self.pkgdir
        # Create a dummy .obscpio file in the outdir
        # Since outdir is created fresh in tar_scm(), we need to be careful.
        # Actually, the service usually runs: obs_scm -> tar.
        # obs_scm creates the .obscpio in outdir.

        # We can simulate this by creating the .obscpio file in the outdir
        # before calling tar_scm, but tar_scm calls mkfreshdir(self.outdir).
        # So we should probably use a different approach or modify testenv.

        # Let's try to use a custom outdir or override mkfreshdir.
        # Alternatively, we can just test the Tar.create_archive method directly.

        from TarSCM.archive import Tar
        from tests.fake_classes import FakeCli
        import shutil

        # Setup a temporary environment
        import tempfile
        tmp = tempfile.mkdtemp()
        try:
            outdir = os.path.join(tmp, 'out')
            os.mkdir(outdir)

            # Mock SCM object
            class MockSCM:
                def __init__(self):
                    self.arch_dir = os.path.join(tmp, 'arch')
                    os.mkdir(self.arch_dir)
                    self.clone_dir = self.arch_dir
                def get_timestamp(self, *args): return 123456789

            scm_obj = MockSCM()

            # Case 1: delete='yes'
            cli_yes = FakeCli()
            cli_yes.outdir = outdir
            cli_yes.delete = True
            cli_yes.extension = 'tar'
            cli_yes.include = []
            cli_yes.exclude = []
            cli_yes.include_re = None
            cli_yes.exclude_re = None
            cli_yes.package_meta = 'no'

            # Create a dummy .obscpio file
            obscpio_path = os.path.join(outdir, 'testpkg-1.0.obscpio')
            with open(obscpio_path, 'w') as f:
                f.write('dummy content')

            tar_arch = Tar()
            tar_arch.create_archive(scm_obj, basename='testpkg', dstname='testpkg-1.0', version='1.0', cli=cli_yes)

            self.assertTrue(os.path.exists(os.path.join(outdir, 'testpkg-1.0.tar')))
            self.assertFalse(os.path.exists(obscpio_path), "The .obscpio file should have been deleted")

            # Case 2: delete='no'
            # Reset environment
            shutil.rmtree(tmp)
            tmp = tempfile.mkdtemp()
            outdir = os.path.join(tmp, 'out')
            os.mkdir(outdir)
            scm_obj = MockSCM()

            cli_no = FakeCli()
            cli_no.outdir = outdir
            cli_no.delete = False
            cli_no.extension = 'tar'
            cli_no.include = []
            cli_no.exclude = []
            cli_no.include_re = None
            cli_no.exclude_re = None
            cli_no.package_meta = 'no'

            obscpio_path = os.path.join(outdir, 'testpkg-1.0.obscpio')
            with open(obscpio_path, 'w') as f:
                f.write('dummy content')

            tar_arch = Tar()
            tar_arch.create_archive(scm_obj, basename='testpkg', dstname='testpkg-1.0', version='1.0', cli=cli_no)

            self.assertTrue(os.path.exists(os.path.join(outdir, 'testpkg-1.0.tar')))
            self.assertTrue(os.path.exists(obscpio_path), "The .obscpio file should NOT have been deleted")

        finally:
            shutil.rmtree(tmp)
