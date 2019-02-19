#!/usr/bin/env python

from commontests import CommonTests
from bzrfixtures import BzrFixtures
from utils       import run_bzr


class BzrTests(CommonTests):

    """Unit tests for 'tar_scm --scm bzr'.

    bzr-specific tests are in this class.  Other shared tests are
    included via the class inheritance hierarchy.
    """

    scm = 'bzr'
    initial_clone_command = 'bzr checkout'
    update_cache_command  = 'bzr update'
    sslverify_false_args  = '-Ossl.cert_reqs=None'
    fixtures_class = BzrFixtures

    def default_version(self):
        return self.rev(2)

    def test_versionformat_rev(self):
        self.tar_scm_std('--versionformat', 'myrev%r.svn')
        self.assertTarOnly(self.basename(version='myrev2.svn'))

    def test_version_versionformat(self):
        self.tar_scm_std('--version', '3.0', '--versionformat', 'myrev%r.svn')
        self.assertTarOnly(self.basename(version='myrev2.svn'))

    def test_versionformat_revision(self):
        self.fixtures.create_commits(4)
        self.tar_scm_std('--versionformat', 'foo%r', '--revision', self.rev(2))
        basename = self.basename(version='foo2')
        th = self.assertTarOnly(basename)
        self.assertTarMemberContains(th, basename + '/a', '2')

    def assertDirentsMtime(self, entries):
        '''Skip this test with bazaar because there seem to be no way to create
        commits with a given timestamp.'''
        return True
