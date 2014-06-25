#!/usr/bin/python
#
# This CLI tool is responsible for running the tests.
# See TESTING.md for more information.

import os
import shutil
import sys
import unittest

from gittests import GitTests
from svntests import SvnTests
from hgtests  import HgTests
from bzrtests import BzrTests
from testenv import TestEnvironment

if __name__ == '__main__':
    suite = unittest.TestSuite()
    testclasses = [
        # If you are only interested in a particular VCS, you can
        # temporarily comment out any of these:
        SvnTests,
        GitTests,
        HgTests,
        BzrTests,
    ]

    if True:  # change to False to run a specific test
        for testclass in testclasses:
            suite.addTests(unittest.TestLoader().loadTestsFromTestCase(testclass))
    else:
        # tweak this to run specific tests
        suite.addTest(HgTests('test_version_versionformat'))
        suite.addTest(HgTests('test_versionformat_dateYYYYMMDD'))
        suite.addTest(HgTests('test_versionformat_timestamp'))

    runner_args = {
        #'verbosity' : 2,
    }
    major, minor, micro, releaselevel, serial = sys.version_info
    if major > 2 or (major == 2 and minor >= 7):
        # New in 2.7
        runner_args['buffer'] = True
        #runner_args['failfast'] = True

    runner = unittest.TextTestRunner(**runner_args)
    result = runner.run(suite)

    # Cleanup:
    if result.wasSuccessful():
        if os.path.exists(TestEnvironment.tmp_dir):
            shutil.rmtree(TestEnvironment.tmp_dir)
        sys.exit(0)
    else:
        print("Left temporary files in %s" % TestEnvironment.tmp_dir)
        sys.exit(1)
