import sys
import os
import argparse
import inspect
import re
import copy
import shutil
import unittest
import six

from mock import MagicMock

from TarSCM.scm.base import Scm

import TarSCM


class SCMBaseTestCases(unittest.TestCase):
    def setUp(self):
        self.basedir        = os.path.abspath(os.path.dirname(__file__))
        # os.getcwd()
        self.tests_dir      = os.path.abspath(os.path.dirname(__file__))
        self.tmp_dir        = os.path.join(self.tests_dir, 'tmp')
        self.outdir         = os.path.join(self.tmp_dir,
                                           self.__class__.__name__, 'out')
        self._prepare_cli()

    def tearDown(self):
        if os.path.exists(self.outdir):
            shutil.rmtree(self.outdir)

    def _prepare_cli(self):
        self.cli = TarSCM.Cli()
        if not os.path.exists(self.outdir):
            os.makedirs(self.outdir)
        self.cli.parse_args(['--outdir', self.outdir, '--scm', 'git'])
        self.cli.snapcraft  = True

    def test_prep_tree_for_archive(self):
        tasks = TarSCM.Tasks(self.cli)
        scm_base = Scm(self.cli, tasks)
        basedir = os.path.join(self.tmp_dir, self.__class__.__name__)
        dir1 = os.path.join(basedir, "test1")
        scm_base.clone_dir = basedir
        os.makedirs(dir1)
        os.symlink('/', os.path.join(basedir, "test3"))

        with self.assertRaises(Exception) as ctx:
            scm_base.prep_tree_for_archive(
                "test2",
                basedir,
                "test1"
            )

        if (hasattr(ctx.exception, 'message')):
            msg = ctx.exception.message
        else:
            msg = ctx.exception

        self.assertRegexpMatches(str(msg), 'No such file or directory')

        scm_base.prep_tree_for_archive("test1", basedir, "test2")

        self.assertEqual(scm_base.arch_dir, os.path.join(basedir, "test2"))

        with self.assertRaises(SystemExit) as ctx:
            scm_base.prep_tree_for_archive("test3", basedir, "test2")

    def test_version_iso_cleanup(self):
        # Avoid get_repocache_hash failure in Scm.__init__
        self.cli.url = ""
        scm_base = Scm(self.cli, None)
        self.assertEqual(scm_base.version_iso_cleanup("2.0.1-3", True), "2.0.1-3")
        self.assertEqual(scm_base.version_iso_cleanup("2.0.1-3", False), "2.0.13")
        self.assertEqual(scm_base.version_iso_cleanup("2.0.1-3"), "2.0.13")
        self.assertEqual(scm_base.version_iso_cleanup("1", True), "1")
        self.assertEqual(scm_base.version_iso_cleanup("1", False), "1")
        self.assertEqual(scm_base.version_iso_cleanup("1"), "1")
        self.assertEqual(scm_base.version_iso_cleanup("1.54-1.2", True), "1.54-1.2")
        self.assertEqual(scm_base.version_iso_cleanup("1.54-1.2", False), "1.541.2")
        self.assertEqual(scm_base.version_iso_cleanup("1.54-1.2"), "1.541.2")
        self.assertEqual(scm_base.version_iso_cleanup("2017-01-02 02:23:11 +0100", True),
                         "20170102T022311")
        self.assertEqual(scm_base.version_iso_cleanup("2017-01-02 02:23:11 +0100", False),
                         "20170102T022311")
        self.assertEqual(scm_base.version_iso_cleanup("2017-01-02 02:23:11 +0100"),
                         "20170102T022311")
