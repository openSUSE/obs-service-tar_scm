import os
import tempfile
import sys
import logging
import re
import hashlib
import shutil
import fcntl
import time
import subprocess
import glob
import locale

from TarSCM.helpers import Helpers
from TarSCM.changes import Changes
from TarSCM.config import Config

try:
    from urllib.parse import urlparse, urlencode
except ImportError:
    from urlparse import urlparse

keyring_import_error = 0

try:
    import keyrings.alt.file
except ImportError:
    keyring_import_error = 1


class Scm():
    def __init__(self, args, task):
        # default settings
        # arch_dir - Directory which is used for the archive
        # e.g. myproject-2.0
        self.arch_dir          = None
        self.repocachedir      = None
        self.clone_dir         = None
        self.lock_file         = None
        self.basename          = None
        self.repodir           = None
        self.user              = None
        self.password          = None
        self._parent_tag       = None
        self._backup_gnupghome = None

        # mandatory arguments
        self.args           = args
        self.task           = task
        self.url            = args.url

        # optional arguments
        self.revision       = args.revision
        if args.user and args.keyring_passphrase:
            if keyring_import_error == 1:
                raise SystemExit('Error while importing keyrings.alt.file but '
                                 '"--user" and "--keyring_passphrase" are set.'
                                 ' Please install keyrings.alt.file!')
            os.environ['XDG_DATA_HOME'] = '/etc/obs/services/tar_scm.d'
            _kr = keyrings.alt.file.EncryptedKeyring()
            _kr.keyring_key = args.keyring_passphrase
            try:
                self.password = _kr.get_password(self.url, args.user)
                if not self.password:
                    raise Exception('No user {u} in keyring for service {s}'
                                    .format(u=args.user, s=self.url))
            except AssertionError:
                raise Exception('Wrong keyring passphrase')
            self.user     = args.user

        # preparation of required attributes
        self.helpers        = Helpers()
        if self.args.changesgenerate:
            self.changes    = Changes()

        self._calc_repocachedir()
        self._final_rename_needed = False

        # proxy support
        self.httpproxy      = None
        self.httpsproxy     = None
        self.noproxy        = None
        self._calc_proxies()

        if self.args.maintainers_asc:
            self._prepare_gpg_settings()

    def __del__(self):
        if self.args.maintainers_asc:
            self._revert_gpg_settings()

    def auth_url(self):
        if self.scm not in ('bzr', 'git', 'hg'):
            return
        auth_patterns = {}
        auth_patterns['bzr'] = {}
        auth_patterns['bzr']['proto']   = r'^(ftp|bzr|https?)://.*'
        auth_patterns['bzr']['already'] = r'^(ftp|bzr|https?)://.*:.*@.*'
        auth_patterns['bzr']['sub']     = r'^((ftp|bzr|https?)://)(.*)'
        auth_patterns['bzr']['format']  = r'\g<1>{user}:{pwd}@\g<3>'
        auth_patterns['git'] = {}
        auth_patterns['git']['proto']   = r'^(ftps?|https?)://.*'
        auth_patterns['git']['already'] = r'^(ftps?|https?)://.*:.*@.*'
        auth_patterns['git']['sub']     = r'^((ftps?|https?)://)(.*)'
        auth_patterns['git']['format']  = r'\g<1>{user}:{pwd}@\g<3>'
        auth_patterns['hg'] = {}
        auth_patterns['hg']['proto']   = r'^https?://.*'
        auth_patterns['hg']['already'] = r'^https?://.*:.*@.*'
        auth_patterns['hg']['sub']     = r'^(https?://)(.*)'
        auth_patterns['hg']['format']  = r'\g<1>{user}:{pwd}@\g<2>'

        if self.user and self.password:
            pattern_proto = re.compile(auth_patterns[self.scm]['proto'])
            pattern = re.compile(auth_patterns[self.scm]['already'])
            if pattern_proto.match(self.url) and not pattern.match(self.url):
                logging.debug('[auth_url] settings credentials from keyring')
                self.url = re.sub(auth_patterns[self.scm]['sub'],
                                  auth_patterns[self.scm]['format'].format(
                                      user=self.user,
                                      pwd=self.password),
                                  self.url)

    def check_scm(self):
        '''check version of scm to proof, it is installed and executable'''
        subprocess.Popen(
            [self.scm, '--version'],
            stdout=subprocess.PIPE
        ).communicate()

    def switch_revision(self):
        '''Switch sources to revision. Dummy implementation for version control
        systems that change revision during fetch/update.
        '''
        return

    def fetch_upstream(self):
        """Fetch sources from repository and checkout given revision."""
        logging.debug("CACHEDIR: '%s'", self.repocachedir)
        logging.debug("SCM: '%s'", self.scm)
        clone_prefix = ""
        if 'clone_prefix' in self.args.__dict__:
            clone_prefix = self.args.__dict__['clone_prefix']

        self._calc_dir_to_clone_to(clone_prefix)
        self.prepare_clone_dir()

        self.lock_cache()

        if not os.path.isdir(self.clone_dir):
            # initial clone
            logging.debug(
                "[fetch_upstream] Initial checkout/clone to directory: '%s'",
                self.clone_dir
            )
            os.mkdir(self.clone_dir)
            self.fetch_upstream_scm()
        else:
            logging.info("Detected cached repository...")
            self.update_cache()

        self.prepare_working_copy()

        # switch_to_revision
        self.switch_revision()

        # git specific: after switching to desired revision its necessary to
        # update
        # submodules since they depend on the actual version of the selected
        # revision
        self.fetch_submodules()

        # obs_scm specific: do not allow running git-lfs to prevent storage
        #  duplication with tar_scm
        if self.args.use_obs_scm:
            self.fetch_lfs()

        self.unlock_cache()

    def fetch_submodules(self):
        """NOOP in other scm's than git"""
        pass

    def fetch_lfs(self):
        """NOOP in other scm's than git"""
        pass

    def detect_changes(self):
        """Detect changes between revisions."""
        if not self.args.changesgenerate:
            return None

        old_servicedata = os.path.join(os.getcwd(), '.old', '_servicedata')
        old_changes_glob = os.path.join(os.getcwd(), '.old', '*.changes')
        if (os.path.isfile(old_servicedata)):
            shutil.copy2(old_servicedata, os.getcwd())
            for filename in glob.glob(old_changes_glob):
                shutil.copy2(filename, os.getcwd())

        chgs = self.changes.read_changes_revision(self.url, os.getcwd(),
                                                  self.args.outdir)

        logging.debug("CHANGES: %s", repr(chgs))

        chgs = self.detect_changes_scm(self.args.subdir, chgs)
        logging.debug("Detected changes:\n%s", repr(chgs))
        return chgs

    def detect_changes_scm(self, subdir, chgs):
        sys.exit("changesgenerate not supported with %s SCM" % self.scm)

    def get_repocache_hash(self, subdir):
        """Calculate hash fingerprint for repository cache."""
        # tar has no u_url
        if self.url:
            u_url = self.url.encode()
            return hashlib.sha256(u_url).hexdigest()
        else:
            return None

    def get_current_commit(self):
        return None

    def _calc_repocachedir(self):
        # check for enabled caches in this order (first wins):
        #   1. local .cache
        #   2. environment
        #   3. user config
        #   4. system wide
        repocachedir  = None
        cwd = os.getcwd()
        if os.path.isdir(os.path.join(cwd, '.cache')):
            repocachedir = os.path.join(cwd, '.cache')

        if repocachedir is None:
            repocachedir = os.getenv('CACHEDIRECTORY')

        if repocachedir is None:
            repocachedir = Config().get('tar_scm', 'CACHEDIRECTORY')

        if repocachedir:
            logging.debug("REPOCACHE: %s", repocachedir)
            self.repohash = self.get_repocache_hash(self.args.subdir)
            if self.repohash:
                self.repocachedir = os.path.join(repocachedir, self.repohash)

    def _calc_proxies(self):
        # check for standard http/https proxy variables
        #   - http_proxy
        #   - https_proxy
        #   - no_proxy
        httpproxy  = os.getenv('http_proxy')
        httpsproxy  = os.getenv('https_proxy')
        noproxy  = os.getenv('no_proxy')

        if httpproxy:
            logging.debug("HTTP proxy found: %s", httpproxy)
            self.httpproxy = httpproxy

        if httpsproxy:
            logging.debug("HTTPS proxy found: %s", httpsproxy)
            self.httpsproxy = httpsproxy

        if noproxy:
            logging.debug("HTTP no proxy found: %s", noproxy)
            self.noproxy = noproxy

    def prepare_clone_dir(self):
        # special case when using osc and creating an obscpio, use
        # current work directory to allow the developer to work inside
        # of the git repo and fetch local changes
        is_snap = sys.argv[0].endswith("snapcraft")
        is_obs_scm = self.args.use_obs_scm
        in_osc = bool(os.getenv('OSC_VERSION'))
        in_git = os.path.isdir('.git')
        if is_snap or (is_obs_scm and in_osc and in_git):
            self.repodir = os.getcwd()

        # construct repodir (the parent directory of the checkout)
        logging.debug("REPOCACHEDIR = '%s'", self.repocachedir)
        if self.repocachedir:
            if not os.path.isdir(self.repocachedir):
                os.makedirs(self.repocachedir)

    def _calc_dir_to_clone_to(self, prefix):
        # separate path from parameters etc.
        url_path = urlparse(self.url)[2].rstrip('/')

        # remove trailing scm extension
        logging.debug("Stripping '%s' extension from '%s'", self.scm, url_path)
        url_path = re.sub(r'\.%s$' % self.scm, '', url_path)
        logging.debug(" - New  url_path: '%s'", url_path)

        # special handling for cloning bare repositories (../repo/.git/)
        url_path = url_path.rstrip('/')

        self.basename = os.path.basename(os.path.normpath(url_path))
        self.basename = prefix + self.basename

        osc_version = 0

        try:
            osc_version = os.environ['OSC_VERSION']
        except:
            pass

        if osc_version == 0:
            tempdir = tempfile.mkdtemp(dir=self.args.outdir)
            self.task.cleanup_dirs.append(tempdir)
        else:
            tempdir = os.getcwd()

        self.repodir = os.path.join(tempdir, self.basename + '_service')

        if self.repocachedir:
            # Update atime and mtime of repocachedir to make it easier
            # for cleanup script
            if os.path.isdir(self.repocachedir):
                os.utime(self.repocachedir, (time.time(), time.time()))
            self.clone_dir = os.path.abspath(os.path.join(self.repocachedir,
                                                          self.basename))
        else:
            self.clone_dir = os.path.abspath(self.repodir)

        logging.debug("[_calc_dir_to_clone_to] CLONE_DIR: %s", self.clone_dir)

    def is_sslverify_enabled(self):
        """Returns ``True`` if the ``sslverify`` option has been enabled or
        not been set (default enabled) ``False`` otherwise."""
        return \
            'sslverify' not in self.args.__dict__ or \
            self.args.__dict__['sslverify']

    def version_iso_cleanup(self, version, debian=False):
        """Reformat timestamp value."""
        version = re.sub(r'([0-9]{4})-([0-9]{2})-([0-9]{2}) +'
                         r'([0-9]{2})([:]([0-9]{2})([:]([0-9]{2}))?)?'
                         r'( +[-+][0-9]{3,4})',
                         r'\1\2\3T\4\6\8',
                         version)
        # avoid removing "-" for Debian packages, which use it to split the
        # upstream vs downstream version
        # for RPM it has to be stripped instead, as it's an illegal character
        if not debian:
            version = re.sub(r'[-:]', '', version)
        return version

    def prepare_working_copy(self):
        pass

    def prep_tree_for_archive(self, subdir, outdir, dstname):
        """Prepare directory tree for creation of the archive by copying the
        requested sub-directory to the top-level destination directory.
        """
        src = os.path.join(self.clone_dir, subdir)
        if not os.path.exists(src):
            raise Exception("%s: No such file or directory" % src)

        self.arch_dir = dst = os.path.join(outdir, dstname)
        if os.path.exists(dst):
            same = os.path.samefile(src, dst) or \
                os.path.samefile(os.path.dirname(src), dst)
            if same:
                return

        r_path = os.path.realpath(src)
        c_dir  = os.path.realpath(self.clone_dir)
        if not r_path.startswith(c_dir):
            sys.exit("--subdir %s tries to escape repository." % subdir)

        logging.debug("copying tree: '%s' to '%s'" % (src, dst))

        shutil.copytree(src, dst, symlinks=True)

    def lock_cache(self):
        pdir = os.path.join(self.clone_dir, os.pardir, '.lock')
        self.lock_file = open(os.path.abspath(pdir), 'w')
        fcntl.lockf(self.lock_file, fcntl.LOCK_EX)

    def unlock_cache(self):
        if self.lock_file and os.path.isfile(self.lock_file.name):
            fcntl.lockf(self.lock_file, fcntl.LOCK_UN)
            self.lock_file.close()
            self.lock_file = None

    def finalize(self):
        self.cleanup()

    def check_url(self):
        return True

    def _prepare_gpg_settings(self):
        logging.debug("preparing gpg settings")
        self._backup_gnupghome = os.getenv('GNUPGHOME')
        gpgdir = tempfile.mkdtemp()
        mode = int('700', 8)
        os.chmod(gpgdir, mode)
        os.putenv('GNUPGHOME', gpgdir)
        logging.debug("Importing file '%s' to gnupghome: '%s'.")
        self.helpers.safe_run(
            ['gpg', '--import', self.args.maintainers_asc],
            cwd=self.clone_dir, interactive=sys.stdout.isatty())

    def _revert_gpg_settings(self):
        if self._backup_gnupghome:
            os.putenv('GNUPGHOME', self._backup_gnupghome)
