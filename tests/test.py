#!/usr/bin/python

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
        SvnTests,
        GitTests,
        HgTests,
        BzrTests,
    ]
    for testclass in testclasses:
        suite.addTests(unittest.TestLoader().loadTestsFromTestCase(testclass))

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
