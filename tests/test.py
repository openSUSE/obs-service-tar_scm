#!/usr/bin/env python2
'''
This CLI tool is responsible for running the tests.
See TESTING.md for more information.
'''

import os
import re
import shutil
import sys

from gittests import GitTests
from svntests import SvnTests
from hgtests  import HgTests
from bzrtests import BzrTests
from testenv import TestEnvironment
from unittestcases import UnitTestCases
from tasks import TasksTestCases
from scm import SCMBaseTestCases

if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest


def str_to_class(string):
    '''Convert string into class'''
    return getattr(sys.modules[__name__], string)


def prepare_testclasses():
    tclasses = [
        # If you are only interested in a particular VCS, you can
        # temporarily comment out any of these or use the env variable
        # TAR_SCM_TC=<comma_separated_list> test.py
        # TAR_SCM_TC=UnitTestCases,TasksTestCases,SCMBaseTestCases,GitTests,SvnTests,HgTests
        UnitTestCases,
        TasksTestCases,
        SCMBaseTestCases,
        GitTests,
        SvnTests,
        HgTests,
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
                m = re.match('^/(.+)/$', arg)
                if m:
                    # regexp mode
                    regexp = m.group(1)
                    matcher = lambda t, r=regexp: re.search(r, t)
                else:
                    matcher = lambda t, a=arg: t == a
                for t in dir(test_class):
                    if not t.startswith('test_'):
                        continue
                    if matcher(t):
                        to_run[t] = True

            for t in to_run.keys():
                testsuite.addTest(test_class(t))
    return testsuite

if __name__ == '__main__':

    suite = prepare_testsuite(
        prepare_testclasses()
    )

    RUNNER_ARGS = {
        # 'verbosity': 2,
        # 'failfast': True,
        'buffer': True
    }

    runner = unittest.TextTestRunner(**RUNNER_ARGS)
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
