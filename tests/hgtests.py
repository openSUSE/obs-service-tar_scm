#!/usr/bin/python

import datetime

from   githgtests  import GitHgTests
from   hgfixtures  import HgFixtures
from   utils       import run_hg

class HgTests(GitHgTests):
    scm = 'hg'
    initial_clone_command = 'hg clone'
    update_cache_command  = 'hg pull'
    fixtures_class = HgFixtures

    abbrev_hash_format = '{node|short}'
    timestamp_format   = '{date}'
    yyyymmdd_format    = '{date|shortdate}'
    yyyymmddhhmmss_format = '{date|isodatesec}'

    def default_version(self):
        return self.rev(2)

    def version(self, rev):
        # Hyphens aren't allowed in version number.  This substitution
        # mirrors the use of sed "s@-@@g" in tar_scm.
        version = "%s%s" % self.timestamps(self.rev(rev))
        return version.replace('-', '')

    def dateYYYYMMDD(self, rev):
        dateobj = datetime.date.fromtimestamp(self.timestamps(rev)[0])
        return dateobj.strftime("%4Y%02m%02d")

    def dateYYYYMMDDHHMMSS(self, rev):
        dateobj = datetime.datetime.fromtimestamp(self.timestamps(rev)[0])
        return dateobj.strftime("%4Y%02m%02dT%02H%02M%02S")
