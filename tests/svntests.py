#!/usr/bin/python

from commontests import CommonTests
from svnfixtures import SvnFixtures
from utils       import run_svn


class SvnTests(CommonTests):

    """Unit tests for 'tar_scm --scm svn'.

    svn-specific tests are in this class.  Other shared tests are
    included via the class inheritance hierarchy.
    """

    scm = 'svn'
    initial_clone_command = 'svn (co|checkout) '
    update_cache_command  = 'svn up(date)?'
    fixtures_class = SvnFixtures

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
