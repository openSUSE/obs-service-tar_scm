#!/usr/bin/python

import datetime
import os
import tarfile

from   githgtests  import GitHgTests
from   gitfixtures import GitFixtures
from   utils       import run_git

class GitTests(GitHgTests):
    scm = 'git'
    initial_clone_command = 'git clone'
    update_cache_command  = 'git fetch'
    fixtures_class = GitFixtures

    abbrev_hash_format = '%h'
    timestamp_format   = '%ct'
    yyyymmdd_format    = '%cd'
    yyyymmddhhmmss_format = '%ci'

    def default_version(self):
        return self.timestamps(self.rev(2))

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

    def test_versionformat_parenttag(self):
        self.tar_scm_std('--versionformat', "@PARENT_TAG@")
        self.assertTarOnly(self.basename(version = self.rev(2)))

    def test_submodule_update(self):
        submod_name = 'submod1'

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
        fix.do_commit(repo_path, new_rev, [ '.gitmodules', submod_name ])
        fix.record_rev(repo_path, new_rev)
        os.chdir(os.path.join(repo_path,submod_name))
        fix.safe_run('checkout tag3')
        os.chdir(repo_path)
        new_rev = fix.next_commit_rev(repo_path)
        fix.do_commit(repo_path, new_rev, [ '.gitmodules', submod_name ])
        fix.record_rev(repo_path, new_rev)

        self.tar_scm_std('--submodules', 'enable','--revision', 'tag3','--version', 'tag3')
        th = tarfile.open(os.path.join(self.outdir , self.basename(version = 'tag3')+'.tar'))
        self.assertTarMemberContains(th ,os.path.join(self.basename(version = 'tag3'),submod_name,'a'),'5')
