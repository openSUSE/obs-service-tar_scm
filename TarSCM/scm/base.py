import os
import ConfigParser
import tempfile
import sys
import logging
import re
import hashlib

from urlparse import urlparse
from ..helpers import helpers
from ..changes import changes


class scm():
    def __init__(self, args, task):
        self.scm          = self.__class__.__name__
        # mandatory arguments
        self.args           = args
        self.task           = task
        self.url            = args.url

        # optional arguments
        self.revision       = args.revision

        # preparation of required attributes
        self.helpers        = helpers()
        if self.args.changesgenerate:
            self.changes    = changes()
        self.repocachedir   = self.get_repocachedir()
        self.repodir        = self.prepare_repodir()

    def switch_revision(self, clone_dir):
        '''Switch sources to revision. Dummy implementation for version control
        systems that change revision during fetch/update.
        '''
        return

    def fetch_upstream(self, **kwargs):
        """Fetch sources from repository and checkout given revision."""
        logging.debug("CACHEDIR: '%s'" % self.repocachedir)
        logging.debug("SCM: '%s'" % self.scm)
        clone_prefix = ""
        if 'clone_prefix' in kwargs:
            clone_prefix = kwargs['clone_prefix']
        clone_dir = self._calc_dir_to_clone_to(clone_prefix)

        if not os.path.isdir(clone_dir):
            # initial clone
            os.mkdir(clone_dir)
            self.fetch_upstream_scm(clone_dir, kwargs=kwargs)
        else:
            logging.info("Detected cached repository...")
            self.update_cache(clone_dir)

        # switch_to_revision
        self.switch_revision(clone_dir)

        # git specific: after switching to desired revision its necessary to
        # update submodules since they depend on the actual version of the
        # selected revision
        self.fetch_submodules(clone_dir, kwargs)

        return clone_dir

    def fetch_submodules(self, clone_dir, kwargs):
        """NOOP in other scm's than git"""
        pass

    def detect_changes(self, args, clone_dir):
        """Detect changes between revisions."""
        if (not args.changesgenerate):
            return None

        changes = self.changes.read_changes_revision(self.url, os.getcwd(),
                                                     args.outdir)

        logging.debug("CHANGES: %s" % repr(changes))

        changes = self.detect_changes_scm(clone_dir, args.subdir, changes)
        logging.debug("Detected changes:\n%s" % repr(changes))
        return changes

    def detect_changes_scm(self, repodir, subdir, changes):
        sys.exit("changesgenerate not supported with %s SCM" % self.scm)

    def get_repocache_hash(self, subdir):
        """Calculate hash fingerprint for repository cache."""
        return hashlib.sha256(self.url).hexdigest()

    def get_current_commit(self, clone_dir):
        return None

    def get_repocachedir(self):
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
            config = self.helpers.get_config_options()
            try:
                repocachedir = config.get('tar_scm', 'CACHEDIRECTORY')
            except ConfigParser.Error:
                pass

        if repocachedir:
            logging.debug("REPOCACHE: %s", repocachedir)

        return repocachedir

    def prepare_repodir(self):
        repocachedir = self.repocachedir
        repodir = None
        # construct repodir (the parent directory of the checkout)
        if repocachedir and os.path.isdir(repocachedir):
            # construct subdirs on very first run
            if not os.path.isdir(os.path.join(repocachedir, 'repo')):
                os.mkdir(os.path.join(repocachedir, 'repo'))
            if not os.path.isdir(os.path.join(repocachedir, 'incoming')):
                os.mkdir(os.path.join(repocachedir, 'incoming'))

            self.repohash = self.get_repocache_hash(self.args.subdir)
            logging.debug("HASH: %s", self.repohash)
            repodir = os.path.join(repocachedir, 'repo', self.repohash)

        # if caching is enabled but we haven't cached something yet
        if repodir and not os.path.isdir(repodir):
            d = os.path.join(repocachedir, 'incoming')
            repodir = tempfile.mkdtemp(dir=d)

        if repodir is None:
            repodir = tempfile.mkdtemp(dir=self.args.outdir)
            self.task.cleanup_dirs.append(repodir)

        # special case when using osc and creating an obscpio, use current work
        # directory to allow the developer to work inside of the git repo and
        # fetch local changes
        if sys.argv[0].endswith("snapcraft") or \
           (self.args.use_obs_scm and os.getenv('OSC_VERSION')):
            repodir = os.getcwd()

        return repodir

    def _calc_dir_to_clone_to(self, prefix):
        # separate path from parameters etc.
        url_path = urlparse(self.url)[2].rstrip('/')

        # remove trailing scm extension
        url_path = re.sub(r'\.%s$' % self.scm, '', url_path)

        # special handling for cloning bare repositories (../repo/.git/)
        url_path = url_path.rstrip('/')

        basename = os.path.basename(os.path.normpath(url_path))
        basename = prefix + basename
        clone_dir = os.path.abspath(os.path.join(self.repodir, basename))
        return clone_dir

    def is_sslverify_enabled(self, kwargs):
        """Returns ``True`` if the ``sslverify`` option has been enabled or
        not been set (default enabled) ``False`` otherwise."""
        return 'sslverify' not in kwargs or kwargs['sslverify']

    def version_iso_cleanup(self, version):
        """Reformat timestamp value."""
        version = re.sub(r'([0-9]{4})-([0-9]{2})-([0-9]{2}) +'
                         r'([0-9]{2})([:]([0-9]{2})([:]([0-9]{2}))?)?'
                         r'( +[-+][0-9]{3,4})', r'\1\2\3T\4\6\8', version)
        version = re.sub(r'[-:]', '', version)
        return version
