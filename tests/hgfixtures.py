#!/usr/bin/env python

from typing import Any, Dict
import os

from tests.fixtures import Fixtures
from tests.utils    import run_hg, file_write_legacy


class HgFixtures(Fixtures):

    """Methods to create and populate a mercurial repository.

    mercurial tests use this class in order to have something to test against.
    """

    def init(self) -> Any:
        self.create_repo()

        self.timestamps  = {}  # type: Dict[Any, Any]
        self.sha1s       = {}  # type: Dict[Any, Any]
        self.short_sha1s = {}  # type: Dict[Any, Any]

        self.create_commits(2)

    def run(self, cmd: Any) -> Any:
        return run_hg(self.repo_path, cmd)

    def create_repo(self) -> Any:
        os.makedirs(self.repo_path)
        os.chdir(self.repo_path)
        self.safe_run('init')
        out = "[ui]\nusername = %s\n" % self.name_and_email
        file_write_legacy('.hg/hgrc', out)

        self.wdir = self.repo_path
        print("created repo %s" % self.repo_path)

    def get_metadata(self, formatstr: Any) -> Any:
        return self.safe_run('log -l1 --template "%s"' % formatstr)[0].decode()

    def record_rev(self, *args: Any) -> Any:
        rev_num = args[0]
        tag = str(rev_num - 1)  # hg starts counting changesets at 0
        self.revs[rev_num] = tag
        epoch_secs, tz_delta_to_utc = \
            self.get_metadata('{date|hgdate}').split()
        self.timestamps[tag] = (float(epoch_secs), int(tz_delta_to_utc))
        self.sha1s[tag] = self.get_metadata('{node}')
        self.short_sha1s[tag] = self.get_metadata('{node|short}')
        self.scmlogs.annotate(
            "Recorded rev %d: id %s, timestamp %s, SHA1 %s" %
            (rev_num,
             tag,
             self.timestamps[tag],
             self.sha1s[tag])
        )

    def get_committer_date(self) -> Any:
        return '--date="%s"' % (str(self.COMMITTER_DATE) + " 0")
