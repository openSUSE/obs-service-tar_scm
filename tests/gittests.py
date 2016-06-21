#!/usr/bin/env python2

import datetime
import os
import re
import tarfile
import textwrap

from githgtests  import GitHgTests
from gitfixtures import GitFixtures
from utils       import run_git


class GitTests(GitHgTests):

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

    def test_changesgenerate_disabled(self):
        self.tar_scm_std('--changesgenerate', 'disable')

    def test_changesgenerate_no_servicedata(self):
        self.tar_scm_std('--changesgenerate', 'enable')
        self._check_servicedata()

    def test_changesgenerate_corrupt_servicedata(self):
        with open(os.path.join(self.pkgdir, '_servicedata'), 'w') as sd:
            sd.write('this is not valid xml')
        self.tar_scm_std('--changesgenerate', 'enable', should_succeed=False)

    def test_changesgenerate_empty_servicedata_file(self):
        sd = open(os.path.join(self.pkgdir, '_servicedata'), 'w')
        sd.close()
        self.tar_scm_std('--changesgenerate', 'enable')
        self._check_servicedata()

    def test_changesgenerate_empty_servicedata_element(self):
        with open(os.path.join(self.pkgdir, '_servicedata'), 'w') as sd:
            sd.write("<servicedata>\n</servicedata>\n")
        self.tar_scm_std('--changesgenerate', 'enable')
        self._check_servicedata()

    def test_changesgenerate_no_changesrevision(self):
        with open(os.path.join(self.pkgdir, '_servicedata'), 'w') as sd:
            sd.write(textwrap.dedent("""\
              <servicedata>
                <service name="tar_scm">
                  <param name="url">%s</param>
                </service>
              </servicedata>
            """ % self.fixtures.repo_url))
        self.tar_scm_std('--changesgenerate', 'enable')
        self._check_servicedata()

    def _write_servicedata(self, rev):
        sha1 = self.sha1s('tag%d' % rev)
        with open(os.path.join(self.pkgdir, '_servicedata'), 'w') as sd:
            sd.write(textwrap.dedent("""\
              <servicedata>
                <service name="tar_scm">
                  <param name="url">%s</param>
                  <param name="changesrevision">%s</param>
                </service>
              </servicedata>
            """ % (self.fixtures.repo_url, sha1)))

    def _write_changes_file(self):
        contents = textwrap.dedent("""\
          -------------------------------------------------------------------
          Fri Oct  3 00:17:50 BST 2014 - %s

          - 2

          -------------------------------------------------------------------
          Thu Sep 18 10:27:14 BST 2014 - %s

          - 1
        """ % (self.fixtures.user_email, self.fixtures.user_email))
        with open(os.path.join(self.pkgdir, 'pkg.changes'), 'w') as f:
            f.write(contents)
        return contents

    def test_changesgenerate_no_change_or_changes_file(self):
        self._write_servicedata(2)
        self.tar_scm_std('--changesgenerate', 'enable')
        self._check_servicedata()

    def test_changesgenerate_no_change_same_changes_file(self):
        self._write_servicedata(2)
        orig_changes = self._write_changes_file()
        self.tar_scm_std('--changesgenerate', 'enable')
        self._check_servicedata()

    def test_changesgenerate_new_commit_no_changes_file(self):
        self._write_servicedata(2)
        self.fixtures.create_commits(1)
        self.tar_scm_std('--changesgenerate', 'enable')
        self._check_servicedata(revision=3)

    def _test_changesgenerate_new_commit_and_changes_file(self, author=None):
        self._write_servicedata(2)
        orig_changes = self._write_changes_file()
        self.fixtures.create_commits(3)

        tar_scm_args = [
            '--changesgenerate', 'enable',
            '--versionformat', '0.6.%h',
        ]
        if author is not None:
            tar_scm_args += ['--changesauthor', self.fixtures.user_email]
        self.tar_scm_std(*tar_scm_args)

        self._check_servicedata(revision=5, expected_dirents=3)

        expected_author = author or 'opensuse-packaging@opensuse.org'
        expected_changes_regexp = self._new_change_entry_regexp(
            expected_author,
            textwrap.dedent("""\
              - Update to version 0.6.%s:
                \* 3
                \* 4
                \* 5
              """) % self.abbrev_sha1s('tag5')
        )
        self._check_changes(orig_changes, expected_changes_regexp)

    def test_changesgenerate_new_commit_and_changes_file_no_version(self):
        self._write_servicedata(2)
        orig_changes = self._write_changes_file()
        self.fixtures.create_commits(3)

        tar_scm_args = [
            '--changesgenerate', 'enable',
            '--version', '',
            '--changesauthor', self.fixtures.user_email
        ]
        self.tar_scm_std(*tar_scm_args)

        self._check_servicedata(revision=5, expected_dirents=3)

        expected_author = self.fixtures.user_email
        expected_changes_regexp = self._new_change_entry_regexp(
            expected_author,
            textwrap.dedent("""\
              - Update to version \d{10}.%s:
                \* 3
                \* 4
                \* 5
              """) % self.abbrev_sha1s('tag5')
        )
        self._check_changes(orig_changes, expected_changes_regexp)

    def _new_change_entry_regexp(self, author, changes):
        return textwrap.dedent("""\
          ^-------------------------------------------------------------------
          \w{3} \w{3} [ \d]\d \d\d:\d\d:\d\d [A-Z]{3} 20\d\d - %s

          %s
          """) % (author, changes)

    def _check_changes(self, orig_changes, expected_changes_regexp):
        new_changes_file = os.path.join(self.outdir, 'pkg.changes')
        self.assertTrue(os.path.exists(new_changes_file))
        with open(new_changes_file) as f:
            new_changes = f.read()
            self.assertNotEqual(orig_changes, new_changes)
            print new_changes
            expected_changes_regexp += "(.*)"
            self.assertRegexpMatches(new_changes, expected_changes_regexp)
            m = re.match(expected_changes_regexp, new_changes, re.DOTALL)
            self.assertEqual(m.group(1), orig_changes)

    def test_changesgenerate_new_commit_and_changes_file(self):
        self._test_changesgenerate_new_commit_and_changes_file(
            self.fixtures.user_email)

    def test_changesgenerate_new_commit_and_changes_file_default_author(self):
        self._test_changesgenerate_new_commit_and_changes_file()

    def test_changesgenerate_new_commit_and_changes_file_with_subdir(self):
        self._write_servicedata(2)
        orig_changes = self._write_changes_file()
        self.fixtures.create_commits(3)
        self.fixtures.create_commits(3, subdir='another_subdir')

        tar_scm_args = [
            '--changesgenerate', 'enable',
            '--versionformat', '0.6.%h',
            '--subdir', 'another_subdir',
            '--changesauthor', self.fixtures.user_email,
        ]

        self.tar_scm_std(*tar_scm_args)

        self._check_servicedata(revision=8, expected_dirents=3)

        expected_author = self.fixtures.user_email
        expected_changes_regexp = self._new_change_entry_regexp(
            expected_author,
            textwrap.dedent("""\
              - Update to version 0.6.%s:
                \* 6
                \* 7
                \* 8
              """) % self.abbrev_sha1s('tag8')
        )
        self._check_changes(orig_changes, expected_changes_regexp)
