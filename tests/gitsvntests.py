#!/usr/bin/env python
# pylint: disable=W1401,E1101
# noqa: W605,E501
import os
import textwrap
import re
import shutil
import glob
import six

from commontests import CommonTests


class GitSvnTests(CommonTests):

    """Unit tests which are shared between git and svn."""

    def _tar_scm_changesgenerate(self, mode, **kwargs):
        self.tar_scm_std(
            '--changesauthor', 'spam',
            '--changesemail', 'a@b.c',
            '--changesgenerate', mode,
            **kwargs
        )

    def test_changesgenerate_disabled(self):
        self._tar_scm_changesgenerate('disable')

    def test_changesgenerate_no_servicedata(self):  # pylint: disable=C0103
        self._tar_scm_changesgenerate('enable')
        self._check_servicedata()

    def test_changesgenerate_corrupt_servicedata(self):  # pylint: disable=C0103
        with open(os.path.join(self.pkgdir, '_servicedata'), 'w') as sdat:
            sdat.write('this is not valid xml')
        self._tar_scm_changesgenerate('enable', should_succeed=False)

    def test_changesgenerate_empty_servicedata_file(self):  # pylint: disable=C0103
        sdat = open(os.path.join(self.pkgdir, '_servicedata'), 'w')
        sdat.close()
        self._tar_scm_changesgenerate('enable')
        self._check_servicedata()

    def test_changesgenerate_empty_servicedata_element(self):   # pylint: disable=C0103
        with open(os.path.join(self.pkgdir, '_servicedata'), 'w') as sdat:
            sdat.write("<servicedata>\n</servicedata>\n")
        self._tar_scm_changesgenerate('enable')
        self._check_servicedata()

    def test_changesgenerate_no_changesrevision(self):  # pylint: disable=C0103
        with open(os.path.join(self.pkgdir, '_servicedata'), 'w') as sdat:
            sdat.write(textwrap.dedent("""\
              <servicedata>
                <service name="tar_scm">
                  <param name="url">%s</param>
                </service>
              </servicedata>""" % self.fixtures.repo_url))
        self._tar_scm_changesgenerate('enable')
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
        with open(os.path.join(self.pkgdir, 'pkg.changes'), 'w') as pkg:
            pkg.write(contents)
        return contents

    def test_changesgenerate_no_change_or_changes_file(self):  # pylint: disable=C0103
        self._write_servicedata(2)
        self._tar_scm_changesgenerate('enable')
        self._check_servicedata()

    def test_changesgenerate_no_change_same_changes_file(self):  # pylint: disable=C0103
        self._write_servicedata(2)
        self._write_changes_file()
        self._tar_scm_changesgenerate('enable')
        self._check_servicedata()

    def test_changesgenerate_new_commit_no_changes_file(self):  # pylint: disable=C0103
        self._write_servicedata(2)
        self.fixtures.create_commits(1)
        self._tar_scm_changesgenerate('enable')
        self._check_servicedata(revision=3)

    def _new_change_entry_regexp(self, author, email, changes):  # pylint: disable=R0201
        return textwrap.dedent("""\
          ^-------------------------------------------------------------------
          \w{3} \w{3} [ \d]\d \d\d:\d\d:\d\d [A-Z]{3} 20\d\d - %s <%s>

          %s
          """) % (author, email, changes)

    def _check_changes(self, orig_changes, expected_changes_regexp):
        new_changes_file = os.path.join(self.outdir, 'pkg.changes')
        self.assertTrue(os.path.exists(new_changes_file))
        with open(new_changes_file) as chg:
            new_changes = chg.read()
            self.assertNotEqual(orig_changes, new_changes)
            print(new_changes)
            expected_changes_regexp += "(.*)"
            six.assertRegex(self, new_changes, expected_changes_regexp)
            reg = re.match(expected_changes_regexp, new_changes, re.DOTALL)
            self.assertEqual(reg.group(1), orig_changes)

    def test_changesgenerate_new_commit_and_changes_file(self):  # pylint: disable=C0103
        self._test_changesgenerate_new_commit_and_changes_file(
            self.fixtures.user_email)

    def test_changesgenerate_new_commit_and_changes_file_default_author(self):  # pylint: disable=C0103
        os.environ['OBS_SERVICE_DAEMON'] = "1"
        self._test_changesgenerate_new_commit_and_changes_file()
        os.environ['OBS_SERVICE_DAEMON'] = "0"

    def _write_servicedata(self, rev):
        with open(os.path.join(self.pkgdir, '_servicedata'), 'w') as sdat:
            sdat.write(textwrap.dedent("""\
              <servicedata>
                <service name="tar_scm">
                  <param name="url">%s</param>
                  <param name="changesrevision">%s</param>
                </service>
              </servicedata>""" % (self.fixtures.repo_url, self.changesrevision(rev))))

    def _test_changesgenerate_new_commit_and_changes_file(self, author=None, email=None):  # pylint: disable=C0103
        self._write_servicedata(2)
        orig_changes = self._write_changes_file()
        self.fixtures.create_commits(3)
        rev = 5
        print("XXXX 1")
        tar_scm_args = self.tar_scm_args()

        if author is not None:
            tar_scm_args += ['--changesauthor', self.fixtures.user_name]

        if email is not None:
            tar_scm_args += ['--changesemail', self.fixtures.user_email]

        print("XXXX 2")
        self.tar_scm_std(*tar_scm_args)

        print("XXXX 3")
        self._check_servicedata(revision=rev, expected_dirents=3)

        rev = self.changesrevision(rev, abbrev=True)

        print("XXXX 4")
        expected_author = author or 'geeko'
        expected_email = email or 'obs-service-tar-scm@invalid'
        expected_changes_regexp = self._new_change_entry_regexp(
            expected_author,
            expected_email,
            textwrap.dedent("""\
              - Update to version 0.6.%s:
                \* 5
                \* 4
                \* 3
              """) % rev
        )
        self._check_changes(orig_changes, expected_changes_regexp)

    def test_changesgenerate_new_commit_and_changes_file_no_version(self):  # pylint: disable=C0103
        self._write_servicedata(2)
        orig_changes = self._write_changes_file()
        self.fixtures.create_commits(3)
        rev = 5

        tar_scm_args = [
            '--changesgenerate', 'enable',
            '--version', '',
            '--changesauthor', self.fixtures.user_name,
            '--changesemail', self.fixtures.user_email
        ]
        self.tar_scm_std(*tar_scm_args)

        self._check_servicedata(revision=rev, expected_dirents=3)

        rev = self.changesrevision(rev, abbrev=True)
        ver_regex = self.changesregex(rev)

        expected_author = self.fixtures.user_name
        expected_email = self.fixtures.user_email
        expected_changes_regexp = self._new_change_entry_regexp(
            expected_author,
            expected_email,
            textwrap.dedent("""\
              - Update to version %s:
                \* 5
                \* 4
                \* 3
              """) % ver_regex
        )
        self._check_changes(orig_changes, expected_changes_regexp)

    def test_changesgenerate_new_commit_and_changes_file_with_subdir(self):   # pylint: disable=C0103
        self._write_servicedata(2)
        orig_changes = self._write_changes_file()
        self.fixtures.create_commits(3)
        self.fixtures.create_commits(3, subdir='another_subdir')
        rev = 8

        tar_scm_args = self.tar_scm_args()

        tar_scm_args += [
            '--subdir', 'another_subdir',
            '--changesauthor', self.fixtures.user_name,
            '--changesemail', self.fixtures.user_email
        ]

        self.tar_scm_std(*tar_scm_args)

        self._check_servicedata(revision=rev, expected_dirents=3)

        expected_author = self.fixtures.user_name
        expected_email = self.fixtures.user_email
        expected_changes_regexp = self._new_change_entry_regexp(
            expected_author,
            expected_email,
            textwrap.dedent("""\
              - Update to version 0.6.%s:
                \* 8
                \* 7
                \* 6
              """) % self.changesrevision(rev, abbrev=True)
        )
        self._check_changes(orig_changes, expected_changes_regexp)

    def test_changesgenerate_old_servicedata(self):   # pylint: disable=C0103
        self._write_servicedata(2)
        orig_changes = self._write_changes_file()
        self.fixtures.create_commits(3)
        rev = 5
        sd_file = os.path.join(self.pkgdir, '_servicedata')
        old_dir = os.path.join(self.pkgdir, '.old')
        os.mkdir(old_dir)
        shutil.move(sd_file, old_dir)
        for filename in glob.glob(os.path.join(self.pkgdir, '*.changes')):
            shutil.move(filename, old_dir)

        tar_scm_args = self.tar_scm_args()

        tar_scm_args += [
            '--changesauthor', self.fixtures.user_name,
            '--changesemail', self.fixtures.user_email
        ]

        self.tar_scm_std(*tar_scm_args)

        self._check_servicedata(revision=rev, expected_dirents=3)

        expected_author = self.fixtures.user_name
        expected_email = self.fixtures.user_email
        expected_changes_regexp = self._new_change_entry_regexp(
            expected_author,
            expected_email,
            textwrap.dedent("""\
              - Update to version 0.6.%s:
                \* 5
                \* 4
                \* 3
              """) % self.changesrevision(rev, abbrev=True)
        )
        self._check_changes(orig_changes, expected_changes_regexp)
