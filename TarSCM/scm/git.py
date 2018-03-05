import sys
import os
import logging
import re
from TarSCM.scm.base import Scm


class Git(Scm):
    scm = 'git'

    def _get_scm_cmd(self):
        """Compose a GIT-specific command line using http proxies"""
        # git should honor the http[s]_proxy variables, but we need to
        # guarantee this, the variables do not work every time
        # the no_proxy variable is honored everytime, so no action
        # is needed here
        scmcmd = ['git']
        if self.httpproxy:
                scmcmd += ['-c', 'http.proxy=' +
                           self.httpproxy]
        if self.httpsproxy:
                scmcmd += ['-c', 'https.proxy=' +
                           self.httpsproxy]
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
        """
        logging.debug("[switch_revision] Starting ...")
        if self.revision is None:
            self.revision = 'master'

        found_revision = None
        revs = [x + self.revision for x in ['origin/', '']]
        for rev in revs:
            if self._ref_exists(rev):
                found_revision = True
                if os.getenv('OSC_VERSION'):
                    stash_text = self.helpers.safe_run(
                                                      self._get_scm_cmd() +
                                                      ['stash'],
                                                      cwd=self.clone_dir)[1]
                    text = self.helpers.safe_run(
                        self._get_scm_cmd() + ['reset', '--hard', rev],
                        cwd=self.clone_dir
                    )[1]
                    if stash_text != "No local changes to save\n":
                        logging.debug("[switch_revision] GIT STASHING")
                        text += self.helpers.safe_run(
                                                      self._get_scm_cmd() +
                                                      ['stash', 'pop'],
                                                      cwd=self.clone_dir)[1]
                else:
                    text = self.helpers.safe_run(
                        self._get_scm_cmd() + ['reset', '--hard', rev],
                        cwd=self.clone_dir
                    )[1]
                # print (text.rstrip())
                break

        if found_revision is None:
            sys.exit('%s: No such revision' % self.revision)

        # only update submodules if they have been enabled
        if os.path.exists(os.path.join(self.clone_dir, '.git', 'modules')):
            self.helpers.safe_run(
                self._get_scm_cmd() + ['submodule', 'update', '--recursive'],
                cwd=self.clone_dir
            )

    def fetch_upstream_scm(self):
        """SCM specific version of fetch_uptream for git."""
        # clone if no .git dir exists
        command = self._get_scm_cmd() + ['clone', self.url, self.clone_dir]
        if not self.is_sslverify_enabled():
            command += ['--config', 'http.sslverify=false']
        if self.repocachedir:
            command.insert(2, '--mirror')
        wdir = os.path.abspath(os.path.join(self.repodir, os.pardir))
        self.helpers.safe_run(
            command, cwd=wdir, interactive=sys.stdout.isatty())

        self.fetch_specific_revision()

    def fetch_specific_revision(self):
        if self.revision and not self._ref_exists(self.revision):
            # fetch reference from url and create locally
            self.helpers.safe_run(
                self._get_scm_cmd() + ['fetch', self.url,
                                       self.revision + ':' + self.revision],
                cwd=self.clone_dir, interactive=sys.stdout.isatty()
            )

    def fetch_submodules(self):
        """Recursively initialize git submodules."""
        if (
                'submodules' in self.args.__dict__ and
                self.args.__dict__['submodules'] == 'enable'
        ):
            self.helpers.safe_run(
                self._get_scm_cmd() + ['submodule', 'update', '--init',
                                       '--recursive'],
                cwd=self.clone_dir
            )
        elif (
                'submodules' in self.args.__dict__ and
                self.args.__dict__['submodules'] == 'master'
        ):
            self.helpers.safe_run(
                self._get_scm_cmd() + ['submodule', 'update', '--init',
                                       '--recursive', '--remote'],
                cwd=self.clone_dir
            )

    def update_cache(self):
        """Update sources via git."""
        # Force origin to the wanted URL in case it switched
        self.helpers.safe_run(
            self._get_scm_cmd() + ['config', 'remote.origin.url', self.url],
            cwd=self.clone_dir,
            interactive=sys.stdout.isatty()
        )

        self.helpers.safe_run(
            self._get_scm_cmd() + ['fetch', '--tags'],
            cwd=self.clone_dir,
            interactive=sys.stdout.isatty()
        )
        self.helpers.safe_run(
            self._get_scm_cmd() + ['fetch'],
            cwd=self.clone_dir,
            interactive=sys.stdout.isatty()
        )

        self.fetch_specific_revision()

    def detect_version(self, args):
        """
        Automatic detection of version number for checked-out GIT repository.
        """
        parent_tag = args['parent_tag']
        versionformat = args['versionformat']
        if versionformat is None:
            versionformat = '%ct.%h'

        if not parent_tag:
            parent_tag = self._detect_parent_tag(args)

        if re.match('.*@PARENT_TAG@.*', versionformat):
            versionformat = self._detect_version_parent_tag(
                parent_tag,
                versionformat)

        if re.match('.*@TAG_OFFSET@.*', versionformat):
            versionformat = self._detect_version_tag_offset(
                parent_tag,
                versionformat)

        version = self.helpers.safe_run(
            self._get_scm_cmd() + ['log', '-n1', '--date=short',
                                   "--pretty=format:%s" % versionformat],
            self.clone_dir
        )[1]
        return self.version_iso_cleanup(version)

    def _detect_parent_tag(self, args):
        parent_tag = ''
        cmd = self._get_scm_cmd() + ['describe', '--tags', '--abbrev=0']
        try:
            if args['match_tag']:
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

        rcode, output = self.helpers.run_cmd(
            self._get_scm_cmd() + ['rev-list', '--count', parent_tag +
                                   '..HEAD'],
            self.clone_dir
        )

        if rcode:
            sys.exit("\033[31m@TAG_OFFSET@ can not be expanded: " +
                     output + "\033[0m")

        tag_offset = output.strip()
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
                                     self.clone_dir)[1]

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

    def detect_changes_scm(self, subdir, chgs):
        """Detect changes between GIT revisions."""
        last_rev = chgs['revision']

        if last_rev is None:
            last_rev = self._log_cmd(
                ['-n1', '--pretty=format:%H', '--skip=10'], subdir)

        current_rev = self._log_cmd(['-n1', '--pretty=format:%H'], subdir)

        if last_rev == current_rev:
            logging.debug("No new commits, skipping changes file generation")
            return

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
        command = self._get_scm_cmd() + ['clone', '--no-checkout']
        use_reference = True
        try:
            if self.args.package_meta:
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

    # no cleanup is necessary for git
    def cleanup(self):
        pass
