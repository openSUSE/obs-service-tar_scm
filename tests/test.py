#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
This CLI tool is responsible for running the tests.
See TESTING.md for more information.
'''
from __future__ import print_function

import os
import re
import shutil
import sys
import unittest

from tests.gittests import GitTests
from tests.svntests import SvnTests
from tests.hgtests  import HgTests
from tests.bzrtests import BzrTests
from tests.testenv import TestEnvironment
from tests.unittestcases import UnitTestCases
from tests.tasks import TasksTestCases
from tests.scm import SCMBaseTestCases
from tests.tartests import TarTestCases
from tests.archiveobscpiotestcases import ArchiveOBSCpioTestCases



def str_to_class(string):
    '''Convert string into class'''
    return getattr(sys.modules[__name__], string)


def prepare_testclasses():
    tclasses = [
        # If you are only interested in a particular VCS, you can
        # temporarily comment out any of these or use the env variable
        # TAR_SCM_TC=<comma_separated_list> test.py
        # export TAR_SCM_TC=UnitTestCases,TasksTestCases,SCMBaseTestCases,GitTests,SvnTests,HgTests,TarTestCases # noqa # pylint: disable=line-too-long
        UnitTestCases,
        TasksTestCases,
        ArchiveOBSCpioTestCases,
        SCMBaseTestCases,
        GitTests,
        SvnTests,
        HgTests,
        TarTestCases,
        BzrTests
    ]

    if os.getenv('TAR_SCM_TC'):
        tclasses = []
        for classname in os.environ['TAR_SCM_TC'].split(','):
            tclasses.append(str_to_class(classname))

    return tclasses


def prepare_testsuite(tclasses):
    testsuite = unittest.TestSuite()

    if len(sys.argv) == 1:
        for testclass in tclasses:
            all_tests = unittest.TestLoader().loadTestsFromTestCase(testclass)
            testsuite.addTests(all_tests)
    else:
        # By default this uses the CLI args as string or regexp
        # matches for names of git tests, but you can tweak this to run
        # specific tests, e.g.:
        # PYTHONPATH=.:tests tests/test.py test_versionformat
        for test_class in tclasses:
            to_run = {}
            for arg in sys.argv[1:]:
                rmatch = re.match('^/(.+)/$', arg)
                if rmatch:
                    # regexp mode
                    regexp = rmatch.group(1)
                    matcher = lambda t, r=regexp: re.search(r, t)
                else:
                    matcher = lambda t, a=arg: t == a
                for tdir in dir(test_class):
                    if not tdir.startswith('test_'):
                        continue
                    if matcher(tdir):
                        to_run[tdir] = True

            for trun in to_run:
                testsuite.addTest(test_class(trun))
    return testsuite


def main():
    test_classes = prepare_testclasses()
    suite = prepare_testsuite(test_classes)

    runner_args = {
        # 'verbosity': 2,
        # 'failfast': True,
        'buffer': True
    }

    runner = unittest.TextTestRunner(**runner_args)
    result = runner.run(suite)

    # Cleanup:
    if result.wasSuccessful():
        if os.path.exists(TestEnvironment.tmp_dir):
            shutil.rmtree(TestEnvironment.tmp_dir)
        sys.exit(0)
    else:
        print("Left temporary files in %s" % TestEnvironment.tmp_dir)
        print("You should remove these prior to the next test run.")
        sys.exit(1)


if __name__ == '__main__':
    main()
