#!/usr/bin/python

import os

from   commontests import CommonTests
from   utils       import run_hg

class GitHgTests(CommonTests):
    mixed_version_template = '%s.master.%s'

    def test_versionformat_abbrevhash(self):
        self.tar_scm_std('--versionformat', self.abbrev_hash_format)
        self.assertTarOnly(self.basename(version = self.sha1s(self.rev(2))))

    def test_versionformat_timestamp(self):
        self.tar_scm_std('--versionformat', self.timestamp_format)
        self.assertTarOnly(self.basename(version = self.version(2)))

    def test_versionformat_dateYYYYMMDD(self):
        self.tar_scm_std('--versionformat', self.yyyymmdd_format)
        self.assertTarOnly(self.basename(version = self.dateYYYYMMDD(self.rev(2))))

    def _mixed_version_format(self):
        return self.mixed_version_template % (self.timestamp_format, self.abbrev_hash_format)

    def _mixed_version(self, rev):
        return self.mixed_version_template % \
            (self.version(rev), self.sha1s(self.rev(rev)))

    def test_versionformat_mixed(self):
        self.tar_scm_std('--versionformat', self._mixed_version_format())
        self.assertTarOnly(self.basename(version = self._mixed_version(2)))

    def test_version_versionformat(self):
        self.tar_scm_std('--version', '3.0', '--versionformat', self._mixed_version_format())
        self.assertTarOnly(self.basename(version = self._mixed_version(2)))

    def test_versionformat_revision(self):
        self.fixtures.create_commits(4)
        self.tar_scm_std('--versionformat', self.abbrev_hash_format, '--revision', self.rev(2))
        basename = self.basename(version = self.sha1s(self.rev(2)))
        th = self.assertTarOnly(basename)
        self.assertTarMemberContains(th, basename + '/a', '2')
