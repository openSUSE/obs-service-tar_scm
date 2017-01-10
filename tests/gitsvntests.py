#!/usr/bin/env python2

import os
import textwrap
import re

from commontests import CommonTests
from utils       import run_git, run_svn


class GitSvnTests(CommonTests):

    """Unit tests which are shared between git and svn."""

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
            print(new_changes)
            expected_changes_regexp += "(.*)"
            self.assertRegexpMatches(new_changes, expected_changes_regexp)
            m = re.match(expected_changes_regexp, new_changes, re.DOTALL)
            self.assertEqual(m.group(1), orig_changes)

    def test_changesgenerate_new_commit_and_changes_file(self):
        self._test_changesgenerate_new_commit_and_changes_file(
            self.fixtures.user_email)

    def test_changesgenerate_new_commit_and_changes_file_default_author(self):
        self._test_changesgenerate_new_commit_and_changes_file()

    def _write_servicedata(self, rev):
        with open(os.path.join(self.pkgdir, '_servicedata'), 'w') as sd:
            sd.write(textwrap.dedent("""\
              <servicedata>
                <service name="tar_scm">
                  <param name="url">%s</param>
                  <param name="changesrevision">%s</param>
                </service>
              </servicedata>
            """ % (self.fixtures.repo_url, self.changesrevision(rev))))

    def _test_changesgenerate_new_commit_and_changes_file(self, author=None):
        self._write_servicedata(2)
        orig_changes = self._write_changes_file()
        self.fixtures.create_commits(3)
        rev = 5

        tar_scm_args = self.tar_scm_args()

        if author is not None:
            tar_scm_args += ['--changesauthor', self.fixtures.user_email]

        self.tar_scm_std(*tar_scm_args)

        self._check_servicedata(revision=rev, expected_dirents=3)

        rev = self.changesrevision(rev, abbrev=True)

        expected_author = author or 'opensuse-packaging@opensuse.org'
        expected_changes_regexp = self._new_change_entry_regexp(
            expected_author,
            textwrap.dedent("""\
              - Update to version 0.6.%s:
                \* 3
                \* 4
                \* 5
              """) % rev
        )
        self._check_changes(orig_changes, expected_changes_regexp)

    def test_changesgenerate_new_commit_and_changes_file_no_version(self):
        self._write_servicedata(2)
        orig_changes = self._write_changes_file()
        self.fixtures.create_commits(3)
        rev = 5

        tar_scm_args = [
            '--changesgenerate', 'enable',
            '--version', '',
            '--changesauthor', self.fixtures.user_email
        ]
        self.tar_scm_std(*tar_scm_args)

        self._check_servicedata(revision=rev, expected_dirents=3)

        rev = self.changesrevision(rev, abbrev=True)
        ver_regex = self.changesregex(rev)

        expected_author = self.fixtures.user_email
        expected_changes_regexp = self._new_change_entry_regexp(
            expected_author,
            textwrap.dedent("""\
              - Update to version %s:
                \* 3
                \* 4
                \* 5
              """) % ver_regex
        )
        self._check_changes(orig_changes, expected_changes_regexp)

    def test_changesgenerate_new_commit_and_changes_file_with_subdir(self):
        self._write_servicedata(2)
        orig_changes = self._write_changes_file()
        self.fixtures.create_commits(3)
        self.fixtures.create_commits(3, subdir='another_subdir')
        rev = 8

        tar_scm_args = self.tar_scm_args()

        tar_scm_args += [
            '--subdir', 'another_subdir',
            '--changesauthor', self.fixtures.user_email,
        ]

        self.tar_scm_std(*tar_scm_args)

        self._check_servicedata(revision=rev, expected_dirents=3)

        expected_author = self.fixtures.user_email
        expected_changes_regexp = self._new_change_entry_regexp(
            expected_author,
            textwrap.dedent("""\
              - Update to version 0.6.%s:
                \* 6
                \* 7
                \* 8
              """) % self.changesrevision(rev, abbrev=True)
        )
        self._check_changes(orig_changes, expected_changes_regexp)
