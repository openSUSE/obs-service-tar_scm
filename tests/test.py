#!/usr/bin/env python2
#
# This CLI tool is responsible for running the tests.
# See TESTING.md for more information.

import os
import re
import shutil
import sys
import unittest



from gittests import GitTests
from svntests import SvnTests
from hgtests  import HgTests
from bzrtests import BzrTests
from testenv import TestEnvironment
from unittestcases import UnitTestCases
from snapcraft import SnapcraftTestCases


if __name__ == '__main__':
    suite = unittest.TestSuite()
    testclasses = [
        # If you are only interested in a particular VCS, you can
        # temporarily comment out any of these:
        SvnTests,
        GitTests,
        HgTests,
        BzrTests,
        UnitTestCases,
        SnapcraftTestCases
    ]

    if len(sys.argv) == 1:
        for testclass in testclasses:
            all_tests = unittest.TestLoader().loadTestsFromTestCase(testclass)
            suite.addTests(all_tests)
    else:
        # By default this uses the CLI args as string or regexp
        # matches for names of git tests, but you can tweak this to run
        # specific tests, e.g.:
        #
        #   suite.addTest(HgTests('test_version_versionformat'))
        #   suite.addTest(HgTests('test_versionformat_dateYYYYMMDD'))
        test_class = GitTests
        #test_class = SnapcraftTestCases
        #test_class = UnitTestCases
        to_run = {}
        for arg in sys.argv[1:]:
            m = re.match('^/(.+)/$', arg)
            if m:
                # regexp mode
                regexp = m.group(1)
                matcher = lambda t: re.search(regexp, t)
            else:
                matcher = lambda t: t == arg
            for t in dir(test_class):
                if not t.startswith('test_'):
                    continue
                if matcher(t):
                    to_run[t] = True

        for t in to_run.keys():
            suite.addTest(test_class(t))

    runner_args = {
        # 'verbosity' : 2,
    }
    major, minor, micro, releaselevel, serial = sys.version_info
    if major > 2 or (major == 2 and minor >= 7):
        # New in 2.7
        runner_args['buffer'] = True
        # runner_args['failfast'] = True

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
