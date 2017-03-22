#!/usr/bin/env python2

import datetime
import os
import re
import tarfile
import textwrap

from githgtests  import GitHgTests
from gitsvntests import GitSvnTests
from gitfixtures import GitFixtures
from utils       import run_git


class GitTests(GitHgTests, GitSvnTests):

    """Unit tests for 'tar_scm --scm git'.

    git-specific tests are in this class.  Other shared tests are
    included via the class inheritance hierarchy.
    """

    scm = 'git'
    initial_clone_command = 'git clone'
    update_cache_command  = 'git fetch'
    sslverify_false_args  = '--config http.sslverify=false'
    fixtures_class = GitFixtures

    abbrev_hash_format = '%h'
    timestamp_format   = '%ct'
    yyyymmdd_format    = '%cd'
    yyyymmddhhmmss_format = '%ci'

    def default_version(self):
        return "%s.%s" % (self.timestamps(self.rev(2)),
                          self.abbrev_sha1s(self.rev(2)))

    def version(self, rev):
        # Hyphens aren't allowed in version number.  This substitution
        # mirrors the use of sed "s@-@@g" in tar_scm.
        return self.timestamps(self.rev(rev)).replace('-', '')

    # This comment line helps align lines with hgtests.py.
    def dateYYYYMMDD(self, rev):
        dateobj = datetime.date.fromtimestamp(float(self.timestamps(rev)))
        return dateobj.strftime("%4Y%02m%02d")

    # This comment line helps align lines with hgtests.py.
    def dateYYYYMMDDHHMMSS(self, rev):
        dateobj = datetime.datetime.fromtimestamp(float(self.timestamps(rev)))
        return dateobj.strftime("%4Y%02m%02dT%02H%02M%02S")

    def rev(self, rev):
        f = self.fixtures
        return f.revs[f.repo_path][rev]

    def timestamps(self, rev):
        f = self.fixtures
        return f.timestamps[f.repo_path][rev]

    def sha1s(self, rev):
        f = self.fixtures
        return f.sha1s[f.repo_path][rev]

    def abbrev_sha1s(self, rev):
        return self.sha1s(rev)[0:7]

    def changesrevision(self, rev, abbrev=False):
        if abbrev:
            return self.abbrev_sha1s('tag%d' % rev)
        return self.sha1s('tag%d' % rev)

    def changesregex(self, rev):
        return '\d{10}.%s' % rev

    def tar_scm_args(self):
        scm_args = [
            '--changesgenerate', 'enable',
            '--versionformat', '0.6.%h',
        ]
        return scm_args

    # N.B. --versionformat gets tested thoroughly in githgtests.py

    def test_parent_tag(self):
        f = self.fixtures
        f.create_commits(1)
        base = f.get_metadata("%H")
        f.create_commits(3)
        self.tar_scm_std("--parent-tag", base,
                         "--versionformat", "@TAG_OFFSET@")
        self.assertTarOnly(self.basename(version="3"))

    def test_versionformat_parenttag(self):
        # the .1 to catch newlines at the end of PARENT_TAG
        self.tar_scm_std('--versionformat', "@PARENT_TAG@.1")
        self.assertTarOnly(self.basename(version=self.rev(2)) + '.1')

    def test_versionformat_tagoffset(self):
        self.tar_scm_std('--versionformat', "@PARENT_TAG@.@TAG_OFFSET@")
        self.assertTarOnly(self.basename(version=self.rev(2) + ".0"))

    def _submodule_fixture(self, submod_name):
        fix = self.fixtures
        repo_path = fix.repo_path
        submod_path = fix.submodule_path(submod_name)

        self.scmlogs.next('submodule-create')
        fix.create_submodule(submod_name)

        self.scmlogs.next('submodule-fixtures')
        fix.create_commits(3, submod_path)
        fix.create_commits(2, submod_path)

        os.chdir(repo_path)
        fix.safe_run('submodule add file://%s' % submod_path)
        new_rev = fix.next_commit_rev(repo_path)
        fix.do_commit(repo_path, new_rev, ['.gitmodules', submod_name])
        fix.record_rev(repo_path, new_rev)
        os.chdir(os.path.join(repo_path, submod_name))
        fix.safe_run('checkout tag3')
        os.chdir(repo_path)
        new_rev = fix.next_commit_rev(repo_path)
        fix.do_commit(repo_path, new_rev, ['.gitmodules', submod_name])
        fix.record_rev(repo_path, new_rev)

    def _submodule_fixture_prepare_branch(self, branch):
        fix = self.fixtures
        repo_path = fix.repo_path
        self.scmlogs.next('prepare-branch')
        os.chdir(repo_path)
        fix.safe_run('checkout -b %s' % branch)
        fix.create_commits(3)

    def test_submodule_update(self):
        submod_name = 'submod1'

        self._submodule_fixture(submod_name)

        self.tar_scm_std('--submodules', 'enable',
                         '--revision', 'tag3',
                         '--version', 'tag3')
        tar_path = os.path.join(self.outdir,
                                self.basename(version='tag3') + '.tar')
        th = tarfile.open(tar_path)
        submod_path = os.path.join(self.basename(version='tag3'),
                                   submod_name, 'a')
        self.assertTarMemberContains(th, submod_path, '5')

    def test_submodule_disabled_update(self):
        submod_name = 'submod1'

        self._submodule_fixture(submod_name)

        self.tar_scm_std('--submodules', 'disable', '--revision', 'tag3',
                         '--version', 'tag3')
        tar_path = os.path.join(self.outdir,
                                self.basename(version='tag3') + '.tar')
        th = tarfile.open(tar_path)
        self.assertRaises(KeyError, th.getmember, os.path.join(
            self.basename(version='tag3'), submod_name, 'a'))

    def test_submodule_in_different_branch(self):
        submod_name = 'submod1'

        rev = 'build'
        self._submodule_fixture_prepare_branch(rev)
        self._submodule_fixture(submod_name)

        self.tar_scm_std('--submodules', 'enable',
                         '--revision', rev,
                         '--version', rev)
        tar_path = os.path.join(self.outdir,
                                self.basename(version=rev) + '.tar')
        th = tarfile.open(tar_path)
        submod_path = os.path.join(self.basename(version=rev),
                                   submod_name, 'a')
        self.assertTarMemberContains(th, submod_path, '3')

    def test_latest_submodule_in_different_branch(self):
        submod_name = 'submod1'

        rev = 'build'
        self._submodule_fixture_prepare_branch(rev)
        self._submodule_fixture(submod_name)

        self.tar_scm_std('--submodules', 'master',
                         '--revision', rev,
                         '--version', rev)
        tar_path = os.path.join(self.outdir,
                                self.basename(version=rev) + '.tar')
        th = tarfile.open(tar_path)
        submod_path = os.path.join(self.basename(version=rev),
                                   submod_name, 'a')
        self.assertTarMemberContains(th, submod_path, '5')

    def _check_servicedata(self, expected_dirents=2, revision=2):
        expected_sha1 = self.sha1s('tag%d' % revision)
        dirents = self.assertNumDirents(self.outdir, expected_dirents)
        self.assertTrue('_servicedata' in dirents,
                        '_servicedata in %s' % repr(dirents))
        sd = open(os.path.join(self.outdir, '_servicedata')).read()
        expected = """\
          <servicedata>
            <service name="tar_scm">
              <param name="url">%s</param>
              <param name="changesrevision">([0-9a-f]{40})</param>
            </service>
          </servicedata>""" % self.fixtures.repo_url
        (expected, count) = re.subn('\s{2,}', '\s*', expected)
        m = re.match(expected, sd)
        self.assertTrue(m, "\n'%s'\n!~ /%s/" % (sd, expected))
        sha1 = m.group(1)
        self.assertEqual(sha1, expected_sha1)

    def test_updatecache_has_tag(self):
        fix = self.fixtures
        fix.create_commits(2)
        self.tar_scm_std("--revision", 'tag2',
                         "--versionformat", "@PARENT_TAG@")
        self.assertTarOnly(self.basename(version="tag2"))

        self.scmlogs.next('prepare-branch')
        repo_path = fix.repo_path
        os.chdir(repo_path)
        fix.safe_run('checkout tag2')
        fix.create_commits(3)
        fix.safe_run('tag -a -m some_message detached_tag')

    def test_versionrewrite(self):
        fix = self.fixtures
        fix.create_commits(2)
        self.tar_scm_std("--revision", 'tag2',
                         "--versionrewrite-pattern", 'tag(\d+)',
                         "--versionrewrite-replacement", '\\1-test',
                         "--versionformat", "@PARENT_TAG@")
        self.assertTarOnly(self.basename(version="2-test"))
