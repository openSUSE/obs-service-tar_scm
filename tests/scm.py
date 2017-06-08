import os
import shutil
import sys

from TarSCM.scm.base import scm

import TarSCM

if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest


class SCMBaseTestCases(unittest.TestCase):
    def setUp(self):
        self.basedir = os.path.abspath(os.path.dirname(__file__))
        # os.getcwd()
        self.tests_dir = os.path.abspath(os.path.dirname(__file__))
        self.tmp_dir = os.path.join(self.tests_dir, 'tmp')
        self.outdir = os.path.join(self.tmp_dir,
                                   self.__class__.__name__, 'out')
        self._prepare_cli()

    def tearDown(self):
        if os.path.exists(self.outdir):
            shutil.rmtree(self.outdir)

    def _prepare_cli(self):
        self.cli = TarSCM.cli()
        if not os.path.exists(self.outdir):
            os.makedirs(self.outdir)
        self.cli.parse_args(['--outdir', self.outdir, '--scm', 'git'])
        self.cli.snapcraft = True

    def test_prep_tree_for_archive(self):
        tasks = TarSCM.tasks()
        scm_base = scm(self.cli, tasks)
        basedir = os.path.join(self.tmp_dir, self.__class__.__name__)
        dir1 = os.path.join(basedir, "test1")
        scm_base.clone_dir = basedir
        os.makedirs(dir1)

        with self.assertRaises(Exception) as ctx:
            scm_base.prep_tree_for_archive(
                "test2",
                basedir,
                "test1"
            )

        self.assertRegexpMatches(ctx.exception.message,
                                 'No such file or directory')

        scm_base.prep_tree_for_archive("test1", basedir, "test2")

        self.assertEqual(scm_base.arch_dir, os.path.join(basedir, "test2"))
