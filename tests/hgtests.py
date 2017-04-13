#!/usr/bin/env python2

from datetime import datetime
import time

from githgtests import GitHgTests
from hgfixtures import HgFixtures


class HgTests(GitHgTests):

    """Unit tests for 'tar_scm --scm hg'.

    hg-specific tests are in this class.  Other shared tests are
    included via the class inheritance hierarchy.
    """

    scm = 'hg'
    initial_clone_command = 'hg clone'
    update_cache_command  = 'hg pull'
    sslverify_false_args  = '--insecure'
    fixtures_class = HgFixtures

    abbrev_hash_format = '{node|short}'
    timestamp_format   = '{date}'
    yyyymmdd_format    = '{date|localdate|shortdate}'
    yyyymmddhhmmss_format = '{date|localdate|isodatesec}'

    def default_version(self):
        return self.rev(2)

    def sha1s(self, rev):
        return self.fixtures.sha1s[rev]

    def abbrev_sha1s(self, rev):
        return self.fixtures.short_sha1s[rev]

    def version(self, rev):
        # Hyphens aren't allowed in version number.  This substitution
        # mirrors the use of sed "s@-@@g" in tar_scm.
        version = "%s%s" % self.timestamps(self.rev(rev))
        return version.replace('-', '')

    def current_utc_offset(self):
        now = time.time()
        offset = (datetime.fromtimestamp(now) -
                  datetime.utcfromtimestamp(now))
        # since total_seconds() isn't available in python 2.6 ...
        return ((((offset.days * 24 * 3600) + offset.seconds) * 10 ** 6) +
                offset.microseconds + 0.0) / 10 ** 6

    def dateYYYYMMDD(self, rev):
        # mercurial has a bug in the localdate filter that makes it apply
        # the current offset from UTC to historic timestamps for timezones
        # that have daylight savings enabled
        dateobj = datetime.utcfromtimestamp(self.timestamps(rev)[0] +
                                            self.current_utc_offset())
        return dateobj.strftime("%4Y%02m%02d")

    def dateYYYYMMDDHHMMSS(self, rev):
        dateobj = datetime.utcfromtimestamp(self.timestamps(rev)[0] +
                                            self.current_utc_offset())
        return dateobj.strftime("%4Y%02m%02dT%02H%02M%02S")

    def test_fetch_upstream(self):
        """Checkout an url that ends with a trailing slash"""
        repo_url = self.fixtures.repo_url + '/'
        args = ['--url', repo_url, '--scm', self.scm]
        self.tar_scm(args)
