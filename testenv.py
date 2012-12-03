#!/usr/bin/python

import os
import shutil
from utils     import mkfreshdir, run_cmd
from scmlogs   import ScmInvocationLogs

class TestEnvironment:
    tests_dir   = os.path.abspath(os.path.dirname(__file__)) # os.getcwd()
    tmp_dir     = tests_dir + '/tmp'
    is_setup    = False

    @classmethod
    def tar_scm_bin(cls):
        tar_scm = cls.tests_dir + '/tar_scm'
        if not os.path.isfile(tar_scm):
            raise RuntimeError, "Failed to find tar_scm executable at " + tar_scm
        return tar_scm

    @classmethod
    def setupClass(cls):
        # deliberately not setUpClass - we emulate the behaviour
        # to support Python < 2.7
        if cls.is_setup:
            return
        print "++++++ setupClass ++++++"
        ScmInvocationLogs.setup_bin_wrapper(cls.scm, cls.tmp_dir)
        os.putenv('DEBUG_TAR_SCM', 'yes')
        cls.is_setup = True

    def calcPaths(self):
        if not self._testMethodName.startswith('test_'):
            raise RuntimeError, "unexpected test method name: " + self._testMethodName
        self.test_name = self._testMethodName[5:]
        self.test_dir  = os.path.join(self.tmp_dir,  self.scm, self.test_name)
        self.pkgdir    = os.path.join(self.test_dir, 'pkg')
        self.outdir    = os.path.join(self.test_dir, 'out')
        self.cachedir  = os.path.join(self.test_dir, 'cache')

    def setUp(self):
        self.setupClass()
        print "++++++ setUp ++++++"

        self.calcPaths()

        self.scmlogs = ScmInvocationLogs(self.scm, self.test_dir)
        self.scmlogs.next('fixtures')

        self.initDirs()

        self.fixtures = self.fixtures_class(self.test_dir, self.scmlogs)
        self.fixtures.setup()

        self.scmlogs.next('start-test')
        self.scmlogs.annotate('Starting %s test' % self.test_name)

        os.putenv('CACHEDIRECTORY', self.cachedir)
        # osc launches source services with cwd as pkg dir
        os.chdir(self.pkgdir)

    def initDirs(self):
        # pkgdir persists between tests to simulate real world use
        # (although a test can choose to invoke mkfreshdir)
        if not os.path.exists(self.pkgdir):
            os.makedirs(self.pkgdir)

        for subdir in ('repo', 'repourl', 'incoming'):
            mkfreshdir(os.path.join(self.cachedir, subdir))

    def disableCache(self):
        os.unsetenv('CACHEDIRECTORY')

    def tearDown(self):
        print "++++++ tearDown ++++++"
        self.postRun()

    def postRun(self):
        print "++++++ postRun +++++++"
        self.service = { 'mode' : 'disabled' }
        if os.path.exists(self.outdir):
            self.simulate_osc_postrun()

    def simulate_osc_postrun(self):
        """
        Simulate osc copying files from temporary --outdir back to
        package source directory, so our tests can catch any
        potential side-effects due to the persistent nature of the
        package source directory.
        """

        temp_dir = self.outdir
        dir = self.pkgdir
        service = self.service

        # This code copied straight out of osc/core.py Serviceinfo.execute():

        if service['mode'] == "disabled" or service['mode'] == "trylocal" or service['mode'] == "localonly" or callmode == "local" or callmode == "trylocal":
            for filename in os.listdir(temp_dir):
                shutil.move( os.path.join(temp_dir, filename), os.path.join(dir, filename) )
        else:
            for filename in os.listdir(temp_dir):
                shutil.move( os.path.join(temp_dir, filename), os.path.join(dir, "_service:"+name+":"+filename) )

    def tar_scm_std(self, *args, **kwargs):
        return self.tar_scm(self.stdargs(*args), **kwargs)

    def tar_scm_std_fail(self, *args):
        return self.tar_scm(self.stdargs(*args), should_succeed=False)

    def stdargs(self, *args):
        return [ '--url', self.fixtures.repo_url, '--scm', self.scm ] + list(args)

    def tar_scm(self, args, should_succeed=True):
        # simulate new temporary outdir for each tar_scm invocation
        mkfreshdir(self.outdir)
        cmdargs = args + [ '--outdir', self.outdir ]
        quotedargs = [ "'%s'" % arg for arg in cmdargs ]
        cmdstr = 'bash %s %s 2>&1' % (self.tar_scm_bin(), " ".join(quotedargs))
        print "\n"
        print "-" * 70
        print "Running", cmdstr
        (stdout, stderr, ret) = run_cmd(cmdstr)
        if stdout:
            print "STDOUT:"
            print "------"
            print stdout,
        if stderr:
            print "STDERR:"
            print "------"
            print stderr,
        print "-" * 70
        succeeded = ret == 0
        self.assertEqual(succeeded, should_succeed)
        return (stdout, stderr, ret)

    def rev(self, rev):
        return self.fixtures.revs[rev]

    def timestamps(self, rev):
        return self.fixtures.timestamps[rev]

    def sha1s(self, rev):
        return self.fixtures.sha1s[rev]

