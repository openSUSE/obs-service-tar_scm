#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import datetime
import os
import re
import tarfile
import shutil
import mock

from tests.githgtests   import GitHgTests
from tests.gitsvntests  import GitSvnTests
from tests.gitfixtures  import GitFixtures
from tests.fake_classes import FakeCli, FakeTasks

from TarSCM.helpers     import Helpers
from TarSCM.scm.git     import Git


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
    def dateYYYYMMDD(self, rev):  # pylint: disable=C0103
        dateobj = datetime.date.fromtimestamp(float(self.timestamps(rev)))
        return dateobj.strftime("%4Y%02m%02d")

    # This comment line helps align lines with hgtests.py.
    def dateYYYYMMDDHHMMSS(self, rev):  # pylint: disable=C0103
        dateobj = datetime.datetime.fromtimestamp(float(self.timestamps(rev)))
        return dateobj.strftime("%4Y%02m%02dT%02H%02M%02S")

    def rev(self, rev):
        fix = self.fixtures
        return fix.revs[fix.repo_path][rev]

    def timestamps(self, rev):
        fix = self.fixtures
        return fix.timestamps[fix.repo_path][rev]

    def sha1s(self, rev):
        fix = self.fixtures
        return fix.sha1s[fix.repo_path][rev]

    def abbrev_sha1s(self, rev):
        return self.sha1s(rev)[0:7]

    def changesrevision(self, rev, abbrev=False):
        if abbrev:
            return self.abbrev_sha1s('tag%d' % rev)
        return self.sha1s('tag%d' % rev)

    def changesregex(self, rev):  # pylint: disable=R0201
        return '\d{10}.%s' % rev  # noqa: W605, pylint: disable=W1401

    def tar_scm_args(self):  # pylint: disable=R0201
        scm_args = [
            '--changesgenerate', 'enable',
            '--versionformat', '0.6.%h',
        ]
        return scm_args

    # N.B. --versionformat gets tested thoroughly in githgtests.py

    def test_parent_tag(self):
        fix = self.fixtures
        fix.create_commits(1)
        base = fix.get_metadata("%H")
        fix.create_commits(3)
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

        self.scmlogs.nextlog('submodule-create')
        fix.create_submodule(submod_name)

        self.scmlogs.nextlog('submodule-fixtures')
        fix.create_commits(3, submod_path)
        fix.create_commits(2, submod_path)

        os.chdir(repo_path)
        fix.safe_run('submodule add file://%s' % submod_path)
        new_rev = fix.next_commit_rev(repo_path)
        fix.do_commit(repo_path, new_rev, ['.gitmodules', submod_name])
        fix.record_rev(new_rev, repo_path)
        os.chdir(os.path.join(repo_path, submod_name))
        fix.safe_run('checkout tag3')
        os.chdir(repo_path)
        new_rev = fix.next_commit_rev(repo_path)
        fix.do_commit(repo_path, new_rev, ['.gitmodules', submod_name])
        fix.record_rev(new_rev, repo_path)

    def _submodule_fixture_prep_branch(self, branch):
        fix = self.fixtures
        repo_path = fix.repo_path
        self.scmlogs.nextlog('prepare-branch')
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
        tar = tarfile.open(tar_path)
        submod_path = os.path.join(self.basename(version='tag3'),
                                   submod_name, 'a')
        self.assertTarMemberContains(tar, submod_path, '5')

    def test_submodule_disabled_update(self):
        submod_name = 'submod1'

        self._submodule_fixture(submod_name)

        self.tar_scm_std('--submodules', 'disable', '--revision', 'tag3',
                         '--version', 'tag3')
        tar_path = os.path.join(self.outdir,
                                self.basename(version='tag3') + '.tar')
        tar = tarfile.open(tar_path)
        self.assertRaises(KeyError, tar.getmember, os.path.join(
            self.basename(version='tag3'), submod_name, 'a'))

    def test_submodule_in_other_branch(self):
        submod_name = 'submod1'

        rev = 'build'
        self._submodule_fixture_prep_branch(rev)
        self._submodule_fixture(submod_name)

        self.tar_scm_std('--submodules', 'enable',
                         '--revision', rev,
                         '--version', rev)
        tar_path = os.path.join(self.outdir,
                                self.basename(version=rev) + '.tar')
        tar = tarfile.open(tar_path)
        submod_path = os.path.join(self.basename(version=rev),
                                   submod_name, 'a')
        self.assertTarMemberContains(tar, submod_path, '3')

    def test_latest_submodule_in_other_branch(self):  # pylint: disable=C0103
        submod_name = 'submod1'

        rev = 'build'
        self._submodule_fixture_prep_branch(rev)
        self._submodule_fixture(submod_name)

        self.tar_scm_std('--submodules', 'master',
                         '--revision', rev,
                         '--version', rev)
        tar_path = os.path.join(self.outdir,
                                self.basename(version=rev) + '.tar')
        tar = tarfile.open(tar_path)
        submod_path = os.path.join(self.basename(version=rev),
                                   submod_name, 'a')
        self.assertTarMemberContains(tar, submod_path, '5')

    def _check_servicedata(self, expected_dirents=2, revision=2):
        expected_sha1 = self.sha1s('tag%d' % revision)
        dirents = self.assertNumDirents(self.outdir, expected_dirents)
        self.assertTrue('_servicedata' in dirents,
                        '_servicedata in %s' % repr(dirents))
        sdat = open(os.path.join(self.outdir, '_servicedata')).read()
        expected = (
            r"\s*<servicedata>"
            r"\s*<service name=\"tar_scm\">"
            r"\s*<param name=\"url\">%s</param>"
            r"\s*<param name=\"changesrevision\">([0-9a-f]{40})</param>"
            r"\s*</service>"
            r"\s*</servicedata>" % self.fixtures.repo_url)
        reg = re.match(expected, sdat)
        self.assertTrue(reg, "\n'%s'\n!~ /%s/" % (sdat, expected))
        sha1 = reg.group(1)
        self.assertEqual(sha1, expected_sha1)

    def test_updatecache_has_tag(self):
        fix = self.fixtures
        fix.create_commits(2)
        self.tar_scm_std("--revision", 'tag2',
                         "--versionformat", "@PARENT_TAG@")
        self.assertTarOnly(self.basename(version="tag2"))

        self.scmlogs.nextlog('prepare-branch')
        repo_path = fix.repo_path
        os.chdir(repo_path)
        fix.safe_run('checkout tag2')
        fix.create_commits(3)
        fix.safe_run('tag -a -m some_message detached_tag')

    def test_versionrewrite(self):
        fix = self.fixtures
        fix.create_commits(2)
        self.tar_scm_std("--revision", 'tag2',
                         "--versionrewrite-pattern", 'tag(\d+)',  # noqa: W605,E501 pylint: disable=W1401
                         "--versionrewrite-replacement", '\\1-test',
                         "--versionformat", "@PARENT_TAG@")
        self.assertTarOnly(self.basename(version="2-test"))

    def test_match_tag(self):
        fix = self.fixtures
        fix.create_commits(2)
        fix.safe_run('tag latest')
        repo_path = fix.repo_path
        os.chdir(repo_path)
        self.tar_scm_std("--match-tag", 'tag*',
                         "--versionformat", "@PARENT_TAG@")
        self.assertTarOnly(self.basename(version="tag4"))
        self.tar_scm_std("--versionformat", "@PARENT_TAG@")
        self.assertTarOnly(self.basename(version="latest"))

    def test_obs_scm_cli(self):
        fix = self.fixtures
        fix.create_commits(2)
        fix.safe_run('tag latest')
        repo_path = fix.repo_path
        os.chdir(repo_path)
        self.tar_scm_std("--match-tag", 'tag*',
                         "--versionformat", "@PARENT_TAG@",
                         "--use-obs-scm", '1')

    def test_gitlab_github_files(self):
        fix = self.fixtures
        fix.create_commits(2)
        fix.safe_run('tag latest')
        repo_path = fix.repo_path
        os.chdir(repo_path)
        os.makedirs("./.gitlab")
        os.makedirs("./.github")
        fix.touch('./.gitlab/test')
        fix.touch('./.github/test')
        fix.safe_run('add .')
        fix.safe_run('commit -a -m "github/gitlab"')
        fix.safe_run('tag gitlab_hub')
        self.tar_scm_std("--revision", "gitlab_hub", "--match-tag",
                         'gitlab_hub', "--versionformat", "@PARENT_TAG@")
        tar_path = os.path.join(self.outdir,
                                self.basename(version='gitlab_hub') + '.tar')
        tar = tarfile.open(tar_path)
        submod_path = os.path.join(self.basename(version='gitlab_hub'))
        hub_path = os.path.join(submod_path, '.github/test')
        lab_path = os.path.join(submod_path, '.gitlab/test')
        self.assertTarMemberContains(tar, hub_path, '')
        self.assertTarMemberContains(tar, lab_path, '')

    def test_no_parent_tag(self):
        fix = self.fixtures
        r_dir = os.path.join(self.test_dir, 'repo')
        os.chdir(r_dir)
        # remove autogenerate gitfixtures
        shutil.rmtree(os.path.join(r_dir))

        # create
        fix.create_repo(r_dir)
        f_h = open('f1', 'a')
        f_h.close()
        fix.safe_run('add .')
        fix.safe_run('commit -m "initial commit"')

        # prepare test
        f_args  = FakeCli()
        f_tasks = FakeTasks()
        git = Git(f_args, f_tasks)

        p_tag = git._detect_parent_tag(f_args)
        self.assertEqual(p_tag, '')

    def test_changesgenerate_unicode(self):
        self._write_servicedata(2)
        self._write_changes_file()
        self.fixtures.create_commit_unicode()
        rev = 3

        tar_scm_args = self.tar_scm_args()

        tar_scm_args += [
            '--changesauthor', self.fixtures.user_email,
        ]

        self.tar_scm_std(*tar_scm_args)

        self._check_servicedata(revision=rev, expected_dirents=3)

    @mock.patch.dict(os.environ, {'http_proxy': 'http://myproxy',
                                  'CACHEDIRECTORY': '/foo'})
    def test_git_mirror_arg_insert(self):
        f_args  = FakeCli()
        f_tasks = FakeTasks()
        git = Git(f_args, f_tasks)
        git.fetch_specific_revision = mock.MagicMock()
        git.repodir = '/tmp'
        git.pardir = '/foo'
        clone_url = 'https://clone_url'
        clone_dir = '/tmp/clone_dir'
        git.url = clone_url
        git.clone_dir = clone_dir
        with mock.patch.object(Helpers, 'safe_run') as mock_save_run:
            git.fetch_upstream_scm()
            ((command,), kwargs) = mock_save_run.call_args  # noqa: E501 pylint: disable=W0612
            expected_command = [
                'git', '-c', 'http.proxy=http://myproxy', 'clone', '--mirror',
                clone_url, clone_dir]
            self.assertEqual(expected_command, command)

    def test_revision_latest_tag(self):
        fix = self.fixtures
        fix.create_commit(fix.wdir)
        fix.create_commit(fix.wdir)
        self.tar_scm_std("--revision", "@PARENT_TAG@")
        sha1 = fix.sha1s[fix.wdir]["tag2"][:7]
        self.assertTarOnly(self.basename(version="1234567890." + sha1))

    def test_without_version(self):
        fix = self.fixtures
        fix.create_commits(2)
        repo_path = fix.repo_path
        os.chdir(repo_path)
        self.tar_scm_std("--without-version", "1")
        tar_path = os.path.join(self.outdir, 'repo.tar')
        self.assertTrue(os.path.isfile(tar_path))

    def test_file_conflicts_revision(self):
        fix = self.fixtures
        fix.create_commits(2)
        repo_path = fix.repo_path
        os.chdir(repo_path)
        os.mkdir("test")
        with open("test/myfile.txt", 'w') as file:
            file.write("just for testing")
        fix.safe_run('add test')
        fix.safe_run('commit -m "added tests"')
        fix.safe_run('tag test')
        self.tar_scm_std("--revision", 'test')

    def test_osc_reset_hard(self):
        fix = self.fixtures

        fix.commit_file_with_tag('0.0.1', 'file.1')
        fix.commit_file_with_tag('0.0.2', 'file.2')

        fix.remove('file.2')

        fix.commit_file_with_tag('0.0.3', 'file.3')
        fix.commit_file_with_tag('0.0.4', 'file.4')

        # prepare local cache like osc would do
        # otherwise the git repo would only contain the .git dir and
        # git._stash_and_merge() would not be executed
        repo_dir = os.path.join(self.pkgdir, 'repo')
        fix.safe_run('clone %s %s' % (fix.wdir, repo_dir))

        # disable cachedirectory (would not be used with osc by default)
        os.environ['CACHEDIRECTORY'] = ""

        # enable osc mode
        os.environ['OSC_VERSION'] = "1"
        self.tar_scm_std("--revision", '0.0.3', '--version', '0.0.3')
        # reset osc mode
        del os.environ['OSC_VERSION']

        # check result
        expected = [
            'repo-0.0.3',
            'repo-0.0.3/a',
            'repo-0.0.3/c',
            'repo-0.0.3/file.1',
            'repo-0.0.3/file.3',
            'repo-0.0.3/subdir',
            'repo-0.0.3/subdir/b'
        ]
        tar = os.path.join(self.test_dir, 'out', 'repo-0.0.3.tar')
        self.assertTarIsDeeply(tar, expected)
