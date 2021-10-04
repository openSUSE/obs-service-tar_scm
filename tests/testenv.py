# -*- coding: utf-8 -*-
# pylint: disable=C0103
import os
import shutil
import sys
import trace
from utils import mkfreshdir
from scmlogs import ScmInvocationLogs
import TarSCM

try:
    from StringIO import StringIO
except:
    from io import StringIO


class TestEnvironment:
    """Framework for testing tar_scm.

    This class provides methods for:

      - setting up and tearing down a test environment similar to what
        'osc service' would provide, and
      - running tar_scm inside that environment.
    """
    tests_dir = os.path.abspath(os.path.dirname(__file__))  # os.getcwd()
    tmp_dir   = os.path.join(tests_dir, 'tmp')
    is_setup  = False

    @classmethod
    def tar_scm_bin(cls):
        tar_scm = os.path.join(cls.tests_dir, '..', 'tar_scm.py')
        if not os.path.isfile(tar_scm):
            msg = "Failed to find tar_scm executable at " + tar_scm
            raise RuntimeError(msg)
        return tar_scm

    @classmethod
    def setupClass(cls):
        # deliberately not setUpClass - we emulate the behaviour
        # to support Python < 2.7
        if cls.is_setup:
            return
        print("--v-v-- begin setupClass for %s --v-v--" % cls.__name__)
        ScmInvocationLogs.setup_bin_wrapper(cls.scm, cls.tests_dir)
        os.putenv('TAR_SCM_CLEAN_ENV', 'yes')
        os.environ['TAR_SCM_CLEAN_ENV'] = 'yes'
        cls.is_setup = True
        print("--^-^-- end   setupClass for %s --^-^--" % cls.__name__)
        print()

    def calcPaths(self):
        if not self._testMethodName.startswith('test_'):
            msg = "unexpected test method name: " + self._testMethodName
            raise RuntimeError(msg)

        self.test_dir  = os.path.join(self.tmp_dir,  self.scm, self.test_name)
        self.pkgdir    = os.path.join(self.test_dir, 'pkg')
        self.homedir   = os.path.join(self.test_dir, 'home')
        self.outdir    = os.path.join(self.test_dir, 'out')
        self.cachedir  = os.path.join(self.test_dir, 'cache')

    def setUp(self):
        print()
        print("=" * 70)
        print(self._testMethodName)
        print("=" * 70)
        print()

        self.test_name = self._testMethodName[5:]

        self.setupClass()

        print("--v-v-- begin setUp for %s --v-v--" % self.test_name)

        self.calcPaths()

        self.scmlogs = ScmInvocationLogs(self.scm, self.test_dir)
        self.scmlogs.nextlog('fixtures')

        self.initDirs()

        self.fixtures = self.fixtures_class(self.test_dir, self.scmlogs)
        self.fixtures.setup()

        self.scmlogs.nextlog('start-test')
        self.scmlogs.annotate('Starting %s test' % self.test_name)

        os.putenv('CACHEDIRECTORY', self.cachedir)
        os.environ['CACHEDIRECTORY'] = self.cachedir
        print("--^-^-- end   setUp for %s --^-^--" % self.test_name)

    def initDirs(self):
        # pkgdir persists between tests to simulate real world use
        # (although a test can choose to invoke mkfreshdir)
        persistent_dirs = [self.pkgdir, self.homedir]
        for i_dir in persistent_dirs:
            if not os.path.exists(i_dir):
                os.makedirs(i_dir)

        # Tests should not depend on the contents of $HOME
        os.putenv('HOME', self.homedir)
        os.environ['HOME'] = self.homedir

        for subdir in ('repo', 'repourl', 'incoming'):
            mkfreshdir(os.path.join(self.cachedir, subdir))

    def disableCache(self):
        os.unsetenv('CACHEDIRECTORY')
        os.environ['CACHEDIRECTORY'] = ""

    def tar_scm_std(self, *args, **kwargs):
        return self.tar_scm(self.stdargs(*args), **kwargs)

    def tar_scm_std_fail(self, *args):
        return self.tar_scm(self.stdargs(*args), should_succeed=False)

    def stdargs(self, *args):
        return [
            '--url', self.fixtures.repo_url,
            '--scm', self.scm
        ] + list(args)

    def tar_scm(self, args, should_succeed=True):
        # simulate new temporary outdir for each tar_scm invocation
        mkfreshdir(self.outdir)

        # osc launches source services with cwd as pkg dir
        # (see run_source_services() in osc/core.py)
        print("chdir to pkgdir: %s" % self.pkgdir)
        os.chdir(self.pkgdir)

        cmdargs = args + ['--outdir', self.outdir]
        sys.argv = [self.tar_scm_bin()] + cmdargs

        old_stdout = sys.stdout
        mystdout   = StringIO()
        sys.stdout = mystdout

        old_stderr = sys.stderr
        mystderr   = StringIO()
        sys.stderr = mystderr

        cmdstr = " ".join(sys.argv)
        print()
        print(">>>>>>>>>>>")
        print("Running %s" % cmdstr)
        print()
        print("start TarSCM.run")
        succeeded = True
        ret = 0
        try:
            TarSCM.run()
        except SystemExit as exp:
            print("raised system exit %r" % exp)
            if exp.code == 0:
                print("exp.code is ok")
                ret = 0
                succeeded = True
            else:
                print("exp.code is not 0")
                sys.stderr.write(exp.code)
                ret = 1
                succeeded = False
        except (NameError, AttributeError) as exp:
            sys.stderr.write(exp)
            ret = 1
            succeeded = False
        except Exception as exp:
            print("Raised Exception %r" % exp)
            if hasattr(exp, 'message'):
                msg = exp.message
            else:
                msg = exp
            sys.stderr.write(str(msg))
            ret = 1
            succeeded = False
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        stdout = mystdout.getvalue()
        stderr = mystderr.getvalue()

        if stdout:
            print("--v-v-- begin STDOUT from tar_scm --v-v--")
            print(stdout)
            print("--^-^-- end   STDOUT from tar_scm --^-^--")

        if stderr:
            print("\n")
            print("--v-v-- begin STDERR from tar_scm --v-v--")
            print(stderr)
            print("--^-^-- end   STDERR from tar_scm --^-^--")
        print("succeeded: %r - should_succeed %r" %
              (succeeded, should_succeed))
        result = ("succeed" if should_succeed else "fail")
        self.assertEqual(succeeded, should_succeed,
                         "expected tar_scm to " + result)

        return (stdout, stderr, ret)

    def rev(self, rev):
        return self.fixtures.revs[rev]

    def timestamps(self, rev):
        return self.fixtures.timestamps[rev]
