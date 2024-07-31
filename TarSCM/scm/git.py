import logging
import os
import re
import sys
import shutil

from TarSCM.scm.base import Scm
from TarSCM.exceptions import GitError


def search_tags(comment, limit=None):
    splitted = comment.split(" ")
    result = []
    while splitted:
        part = splitted.pop(0)
        if part == "tag:":
            result.append(splitted.pop(0))
        if limit and len(result) > limit:
            break
    return result


class Git(Scm):
    scm = 'git'
    _stash_pop_required = False
    partial_clone = False

    def _get_scm_cmd(self):
        """Compose a GIT-specific command line using http proxies"""
        # git should honor the http[s]_proxy variables, but we need to
        # guarantee this, the variables do not work every time
        # the no_proxy variable is honored everytime, so no action
        # is needed here
        scmcmd = ['git']
        if self.httpproxy:
            scmcmd += ['-c', 'http.proxy=' + self.httpproxy]
        if self.httpsproxy:
            scmcmd += ['-c', 'https.proxy=' + self.httpsproxy]
        return scmcmd

    def switch_revision(self):
        """Switch sources to revision. The git revision may refer to any of the
        following:

        - explicit SHA1: a1b2c3d4....
        - the SHA1 must be reachable from a default clone/fetch (generally,
          must be reachable from some branch or tag on the remote).
        - short branch name: "master", "devel" etc.
        - explicit ref: refs/heads/master, refs/tags/v1.2.3,
          refs/changes/49/11249/1
        - wildcard to match latest tag: @PARENT_TAG@
        """
        logging.debug("[switch_revision] Starting ...")
        self.revision = self.revision or 'master'

        if self.revision == "@PARENT_TAG@":
            self.revision = self._detect_parent_tag()
            if not self.revision:
                sys.exit("\033[31mNo parent tag present for the checked out "
                         "revision, thus @PARENT_TAG@ cannot be expanded."
                         "\033[0m")

        if self.args.latest_signed_commit:
            self.revision = self.find_latest_signed_commit('HEAD')
            if not self.revision:
                sys.exit("\033[31mNo signed commit found!"
                         "\033[0m")

        if self.args.latest_signed_tag:
            self.revision = self.find_latest_signed_tag()
            if not self.revision:
                sys.exit("\033[31mNo signed commit found!"
                         "\033[0m")

        if os.getenv('OSC_VERSION') and \
           len(os.listdir(self.clone_dir)) > 1:
            # Ensure that the call of "git stash" is done with
            # LANG=C to get a reliable output
            self._stash_and_merge()

        # is doing the checkout in a hard way
        # may not exist before when using cache
        self.helpers.safe_run(
            self._get_scm_cmd() + ['reset', '--hard', self.revision],
            cwd=self.clone_dir
        )

        # only update submodules if they have been enabled
        if os.path.exists(os.path.join(self.clone_dir, '.git', 'modules')):
            self.helpers.safe_run(
                self._get_scm_cmd() + ['submodule', 'update', '--recursive'],
                cwd=self.clone_dir
            )

    def _stash_and_merge(self):
        lang_bak = None
        if 'LANG' in os.environ:
            lang_bak = os.environ['LANG']
            os.environ['LANG'] = "C"

        logging.debug("[switch_revision] GIT STASHING")
        stash_text = self.helpers.safe_run(
            self._get_scm_cmd() + ['stash'],
            cwd=self.clone_dir)[1]

        # merge may fail when not a remote branch, that is fine
        rcode, output = self.helpers.run_cmd(
            self._get_scm_cmd() + ['merge', 'origin/' + self.revision],
            cwd=self.clone_dir,
            interactive=True)

        # we must test also merge a possible local tag/branch
        # because the user may have changed the revision in _service file
        if rcode != 0 and 'not something we can merge' in output:
            self.helpers.run_cmd(
                self._get_scm_cmd() + ['merge', self.revision],
                cwd=self.clone_dir,
                interactive=True)

        # validate the existens of the revision
        if self.revision and not self._ref_exists(self.revision):
            sys.exit('%s: No such revision' % self.revision)

        if stash_text != "No local changes to save\n":
            self._stash_pop_required = [self.get_current_branch(),
                                        self.get_current_commit()]

        if lang_bak:
            os.environ['LANG'] = lang_bak

    def fetch_upstream_scm(self):
        """SCM specific version of fetch_uptream for git."""
        self.auth_url()

        # clone if no .git dir exists
        command = self._get_scm_cmd() + ['clone',
                                         self.url, self.clone_dir]
        if self.partial_clone:
            command.insert(-2, '--filter=tree:0')
        if not self.is_sslverify_enabled():
            command += ['--config', 'http.sslverify=false']
        if self.repocachedir and not self.partial_clone:
            command.insert(command.index('clone') + 1, '--mirror')
        wdir = os.path.abspath(os.path.join(self.repodir, os.pardir))
        try:
            self.helpers.safe_run(
                command, cwd=wdir, interactive=sys.stdout.isatty())
        except SystemExit as exc:
            os.removedirs(os.path.join(wdir, self.clone_dir))
            raise exc
        if self.partial_clone:
            config_command = self._get_scm_cmd() + ['config', '--local',
                                                    'extensions.partialClone',
                                                    'origin']
            self.helpers.safe_run(
                config_command, cwd=self.clone_dir,
                interactive=sys.stdout.isatty())

            argsd = self.args.__dict__
            if 'submodules' not in argsd:
                cfg_cmd = self._get_scm_cmd() + ['config', '--local',
                                                 'fetch.recurseSubmodules',
                                                 'false']
                self.helpers.safe_run(
                    cfg_cmd, cwd=self.clone_dir,
                    interactive=sys.stdout.isatty())

        if self.revision == "@PARENT_TAG@":
            self.revision = self._detect_parent_tag()
            if not self.revision:
                sys.exit("\033[31mNo parent tag present for the checked out "
                         "revision, thus @PARENT_TAG@ cannot be expanded."
                         "\033[0m")

        self.fetch_specific_revision()

        if self.revision and not self.repocachedir:
            self.helpers.safe_run(
                self._get_scm_cmd() + ['checkout', self.revision],
                cwd=self.clone_dir
            )

    def fetch_specific_revision(self):
        if self.revision and not self._ref_exists(self.revision):
            rev = self.revision + ':' + self.revision
            command = self._get_scm_cmd() + ['fetch', self.url, rev]
            if self.partial_clone:
                command.insert(-2, '--filter=tree:0')
            # fetch reference from url and create locally
            self.helpers.safe_run(
                command,
                cwd=self.clone_dir, interactive=sys.stdout.isatty()
            )

    def fetch_submodules(self):
        """Recursively initialize git submodules."""
        argsd = self.args.__dict__
        if 'submodules' in argsd and argsd['submodules'] == 'enable':
            self.helpers.safe_run(
                self._get_scm_cmd() + ['submodule', 'update', '--init',
                                       '--recursive'],
                cwd=self.clone_dir
            )
        elif 'submodules' in argsd and \
             argsd['submodules'] in ['main', 'master']:
            self.helpers.safe_run(
                self._get_scm_cmd() + ['submodule', 'update', '--init',
                                       '--recursive', '--remote'],
                cwd=self.clone_dir
            )

    def fetch_lfs(self):
        """Initialize git lfs objects."""
        argsd = self.args.__dict__
        if 'lfs' in argsd and argsd['lfs'] == 'enable':
            self.helpers.safe_run(
                self._get_scm_cmd() + ['lfs', 'fetch'],
                cwd=self.clone_dir
            )
            self.helpers.safe_run(
                self._get_scm_cmd() + ['lfs', 'checkout'],
                cwd=self.clone_dir
            )

    def update_cache(self):
        """Update sources via git."""
        # Force origin to the wanted URL in case it switched
        self.auth_url()
        try:
            self.helpers.safe_run(
                self._get_scm_cmd() + ['config', 'remote.origin.url',
                                       self.url],
                cwd=self.clone_dir,
                interactive=sys.stdout.isatty()
            )

            command = self._get_scm_cmd() + ['fetch', '--tags']
            if self.partial_clone:
                command.insert(-1, '--filter=tree:0')

            self.helpers.safe_run(
                command,
                cwd=self.clone_dir,
                interactive=sys.stdout.isatty()
            )

            command = self._get_scm_cmd() + ['fetch']
            if self.partial_clone:
                command.append('--filter=tree:0')

            self.helpers.safe_run(
                command,
                cwd=self.clone_dir,
                interactive=sys.stdout.isatty()
            )

        except SystemExit as exc:
            logging.error("Corrupt clone_dir '%s' detected.", self.clone_dir)
            obs_service_daemon = os.getenv('OBS_SERVICE_DAEMON')
            osc_version = os.getenv('OSC_VERSION')
            if obs_service_daemon and not osc_version:
                logging.info("Removing corrupt cache!")
                shutil.rmtree(self.clone_dir)
                self.fetch_upstream_scm()
            else:
                logging.info("Please fix corrupt cache directory!")
                raise exc

    def detect_version(self, args):
        """
        Automatic detection of version number for checked-out GIT repository.
        """
        self._parent_tag = args['parent_tag'] or self._parent_tag
        versionformat = args['versionformat']
        if versionformat is None:
            versionformat = '%ct.%h'

        if not self._parent_tag:
            self._parent_tag = self._detect_parent_tag(args)

        if re.match('.*@PARENT_TAG@.*', versionformat):
            versionformat = self._detect_version_parent_tag(
                self._parent_tag,
                versionformat)

        if re.match('.*@TAG_OFFSET@.*', versionformat):
            versionformat = self._detect_version_tag_offset(
                self._parent_tag,
                versionformat)
        log_cmd = self._get_scm_cmd() + ['log', '-n1', '--date=format:%Y%m%d',
                                         '--no-show-signature',
                                         "--pretty=format:%s" % versionformat]
        if self.revision:
            log_cmd.append('--source')
            log_cmd.append(self.revision)
            revpath = os.path.join(self.clone_dir, self.revision)
            if os.path.exists(revpath):
                log_cmd.append('--')

        version = self.helpers.safe_run(log_cmd, self.clone_dir)[1]
        return version

    def _detect_parent_tag(self, args=None):
        parent_tag = ''
        cmd = self._get_scm_cmd() + ['describe', '--tags', '--abbrev=0']
        try:
            if args and args['match_tag']:
                cmd.append("--match=%s" % args['match_tag'])
        except KeyError:
            pass
        rcode, output = self.helpers.run_cmd(cmd, self.clone_dir)

        if rcode == 0:
            # strip to remove newlines
            parent_tag = output.strip()

        return parent_tag

    def _detect_version_parent_tag(self, parent_tag, versionformat):  # noqa pylint: disable=no-self-use
        if not parent_tag:
            sys.exit("\033[31mNo parent tag present for the checked out "
                     "revision, thus @PARENT_TAG@ cannot be expanded."
                     "\033[0m")

        versionformat = re.sub('@PARENT_TAG@', parent_tag,
                               versionformat)
        return versionformat

    def _detect_version_tag_offset(self, parent_tag, versionformat):
        if not parent_tag:
            sys.exit("\033[31m@TAG_OFFSET@ cannot be expanded, "
                     "as no parent tag was discovered.\033[0m")

        cmd = self._get_scm_cmd()
        cmd.extend(['rev-list', '--count', parent_tag + '..HEAD'])
        rcode, out = self.helpers.run_cmd(cmd, self.clone_dir)

        if rcode:
            msg = "\033[31m@TAG_OFFSET@ can not be expanded: {}\033[0m"
            msg = msg.format(out)
            sys.exit(msg)

        tag_offset = out.strip()
        versionformat = re.sub('@TAG_OFFSET@', tag_offset,
                               versionformat)
        return versionformat

    def get_timestamp(self):
        data = {"parent_tag": None, "versionformat": "%ct"}
        timestamp = self.detect_version(data)
        return int(timestamp)

    def get_current_commit(self):
        return self.helpers.safe_run(self._get_scm_cmd() + ['rev-parse',
                                                            'HEAD'],
                                     self.clone_dir)[1].rstrip()

    def get_current_branch(self):
        return self.helpers.safe_run(self._get_scm_cmd() + ['rev-parse',
                                                            '--abbrev-ref',
                                                            'HEAD'],
                                     self.clone_dir)[1].rstrip()

    def _ref_exists(self, rev):
        rcode, _ = self.helpers.run_cmd(
            self._get_scm_cmd() + ['rev-parse', '--verify', '--quiet', rev],
            cwd=self.clone_dir,
            interactive=sys.stdout.isatty()
        )
        return rcode == 0

    def _log_cmd(self, cmd_args, subdir):
        """ Helper function to call 'git log' with args"""
        cmd = self._get_scm_cmd() + ['log'] + cmd_args
        if subdir:
            cmd += ['--', subdir]
        return self.helpers.safe_run(cmd, cwd=self.clone_dir)[1]

    def detect_changes_scm(self, chgs):
        """Detect changes between GIT revisions."""
        last_rev = chgs['revision']
        subdir = self.args.subdir

        if last_rev is None:
            last_rev = self._log_cmd(
                ['-n1', '--pretty=format:%H', '--skip=10'], subdir)

        current_rev = self._log_cmd(['-n1', '--pretty=format:%H'], subdir)

        if last_rev == current_rev:
            logging.debug("No new commits, skipping changes file generation")
            return None

        dbg_msg = "Generating changes between %s and %s" % (last_rev,
                                                            current_rev)
        if subdir:
            dbg_msg += " (for subdir: %s)" % (subdir)

        logging.debug(dbg_msg)

        lines = self._log_cmd(['--no-merges',
                               '--pretty=format:%s',
                               "%s..%s" % (last_rev, current_rev)],
                              subdir)

        chgs['revision'] = current_rev
        chgs['lines'] = lines.split('\n')
        return chgs

    def prepare_working_copy(self):
        if not self.repocachedir:
            return

        # We use a temporary shared clone to avoid race conditions
        # between multiple services
        org_clone_dir = self.clone_dir
        self.clone_dir = self.repodir
        command = self._get_scm_cmd() + ['clone',
                                         '--no-checkout']
        if self.partial_clone:
            command.insert(-1, '--filter=tree:0')
        use_reference = True

        try:
            if (self.args.package_meta and not self.partial_clone):
                logging.info("Not using '--reference'")
                use_reference = False
        except KeyError:
            pass

        if use_reference:
            command.extend(['--reference', org_clone_dir, self.url])
        else:
            command.append(org_clone_dir)
        command.append(self.clone_dir)
        wdir = os.path.abspath(os.path.join(self.clone_dir, os.pardir))
        self.helpers.safe_run(
            command, cwd=wdir, interactive=sys.stdout.isatty())
        if self.partial_clone:
            config_command = self._get_scm_cmd() + ['config', '--local',
                                                    'extensions.partialClone',
                                                    'origin']

            self.helpers.safe_run(
                config_command, cwd=self.clone_dir,
                interactive=sys.stdout.isatty())
            argsd = self.args.__dict__
            if 'submodules' not in argsd:
                cfg_cmd = self._get_scm_cmd() + ['config', '--local',
                                                 'fetch.recurseSubmodules',
                                                 'false']
                self.helpers.safe_run(
                    cfg_cmd, cwd=self.clone_dir,
                    interactive=sys.stdout.isatty())

        if self.revision == "@PARENT_TAG@":
            self.revision = self._detect_parent_tag()
            if not self.revision:
                sys.exit("\033[31mNo parent tag present for the checked out "
                         "revision, thus @PARENT_TAG@ cannot be expanded."
                         "\033[0m")

        if self.revision and not self._ref_exists(self.revision):
            refspec = self.revision + ":" + self.revision
            if self.partial_clone:
                command.insert(-3, '--filter=tree:0')
            cmd = self._get_scm_cmd() + ['fetch', 'origin',
                                         refspec]
            self.helpers.safe_run(
                cmd, cwd=self.clone_dir, interactive=sys.stdout.isatty())

    def cleanup(self):
        logging.debug("Doing cleanup")
        if self._stash_pop_required:
            logging.debug("Stash pop required!")
            branch = self._stash_pop_required[0]
            commit = self._stash_pop_required[1]
            self.helpers.safe_run(
                self._get_scm_cmd() + ['checkout', branch],
                self.clone_dir)

            self.helpers.safe_run(
                self._get_scm_cmd() + ['reset', '--hard', commit],
                self.clone_dir)

            self.helpers.safe_run(
                self._get_scm_cmd() + ['stash', 'pop'],
                cwd=self.clone_dir,
                interactive=True)
            self._stash_pop_required = False
        return True

    def check_url(self):
        """check if url is a remote url"""

        # no local path allowed
        if re.match('^file:', self.url):
            return False

        if '://' in self.url:
            return bool(re.match("^(https?|ftps?|git|ssh)://", self.url))

        # e.g. user@host.xy:path/to/repo
        if re.match('^[^/]+:', self.url):
            return True

        # Deny by default, might be local path
        return False

    def find_latest_signed_commit(self, commit):
        if not commit:
            commit = 'HEAD'
        cmd = ['git', 'rev-list', '-n1', commit]
        result = self.helpers.safe_run(cmd, cwd=self.clone_dir)
        commit = result[1].rstrip()

        while commit:
            parents = self.get_parents(commit)
            (commit, c_ok) = self.check_commit(commit, parents)
            if c_ok:
                return commit
        return None

    def check_commit(self, current_commit, parents):
        # pylint: disable=R0911,R0912
        left_parent = None
        if parents:
            left_parent = parents[0]
        right_parent = None
        if len(parents) > 1:
            right_parent = parents[1]
        # skip octopus merges and proceed with left parent
        if len(parents) > 2:
            return (left_parent, 0)
        if not current_commit:
            return ('', 0)

        cmd = ['git', 'verify-commit', current_commit]
        result = self.helpers.run_cmd(cmd, cwd=self.clone_dir)
        if not result[0]:
            return (current_commit, 1)

        if right_parent:
            c_ok = self.check_commit(
                current_commit,
                [right_parent])
            if c_ok[1]:
                parents = self.get_parents(left_parent)
                if len(parents) > 1:
                    mie = self.merge_is_empty(current_commit)
                    if mie:
                        c_ok = self.check_commit(
                            current_commit,
                            [left_parent])
                        return (current_commit, c_ok[1])
                else:
                    c_ok = self.check_commit(
                        current_commit,
                        [left_parent])
                    if c_ok[1]:
                        return (current_commit, 1)
        elif left_parent:
            parents = self.get_parents(left_parent)
            if len(parents) > 1:
                c_ok = self.check_commit(current_commit, parents)
                if c_ok[1]:
                    return (left_parent, 1)
            else:
                cmd = ['git', 'verify-commit', left_parent]
                result = self.helpers.run_cmd(cmd, cwd=self.clone_dir)
                if not result[0]:
                    return (left_parent, 1)

        return (left_parent, 0)

    def merge_is_empty(self, sha1):
        cmd  = ['git', 'diff-tree', '--cc', sha1]
        result = self.helpers.safe_run(cmd, cwd=self.clone_dir)
        lines = result[1].split("\n")
        if lines[1]:
            return 0
        return 1

    def get_parents(self, sha1):
        cmd  = ['git', 'rev-list', '--parents', '-n', '1', sha1]
        result = self.helpers.safe_run(cmd, cwd=self.clone_dir)
        parents = result[1].rstrip().split(" ")
        fcm = parents.pop(0)
        if fcm != sha1:
            raise GitError("First commit %s no equal sha1 %s" % (fcm, sha1))
        if parents:
            return parents
        return []

    def find_latest_signed_tag(self):
        revision = None

        result = self.helpers.safe_run(
            ['git', 'log', '--pretty=format:%H %G? %h %D', "--topo-order"],
            cwd=self.clone_dir)

        lines = result[1].split("\n")
        while lines:
            line = lines.pop(0)
            commit = line.split(" ", 3)
            if len(commit) > 3:
                for tag in search_tags(commit[3]):
                    tag = re.sub(",$", '', tag)
                    verify = self.helpers.run_cmd(
                        ['git', 'verify-tag', tag],
                        cwd=self.clone_dir)
                    if verify[0] == 0:
                        revision = self._parent_tag = tag
                        break
            if revision:
                break

        if not revision:
            logging.debug("No signed tag found!")

        return revision
