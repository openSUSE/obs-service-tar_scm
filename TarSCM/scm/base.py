import os
import ConfigParser
import tempfile
import sys
import logging
import re
import hashlib
import shutil

from urlparse import urlparse
from ..helpers import helpers
from ..changes import changes

class scm():
    def __init__(self,args,task):
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
        self.clone_dir      = None

	# arch_dir - Directory which is used for the archive
	# e.g. myproject-2.0
	self.arch_dir	    = None


    def switch_revision(self):
        '''Switch sources to revision. Dummy implementation for version control
        systems that change revision during fetch/update.
        '''
        return

    def fetch_upstream(self):
        """Fetch sources from repository and checkout given revision."""
        logging.debug("CACHEDIR: '%s'" % self.repocachedir)
        logging.debug("SCM: '%s'" % self.scm)
        clone_prefix = ""
        if 'clone_prefix' in self.args.__dict__:
            clone_prefix = self.args.__dict__['clone_prefix']

        self._calc_dir_to_clone_to(clone_prefix)

        if not os.path.isdir(self.clone_dir):
            # initial clone
            os.mkdir(self.clone_dir)
            self.fetch_upstream_scm()
        else:
            logging.info("Detected cached repository...")
            self.update_cache()
        
        # switch_to_revision
        self.switch_revision()

        # git specific: after switching to desired revision its necessary to update
        # submodules since they depend on the actual version of the selected
        # revision
        self.fetch_submodules()

    def fetch_submodules(self):
        """NOOP in other scm's than git"""
        pass

    def detect_changes(self):
        """Detect changes between revisions."""
        if (not self.args.changesgenerate):
            return None

        changes = self.changes.read_changes_revision(self.url, os.getcwd(), self.args.outdir)

        logging.debug("CHANGES: %s" % repr(changes))

        changes = self.detect_changes_scm(self.args.subdir, changes)
        logging.debug("Detected changes:\n%s" % repr(changes))
        return changes

    def detect_changes_scm(self, subdir, changes):
        sys.exit("changesgenerate not supported with %s SCM" % self.scm)

    def get_repocache_hash(self, subdir):
        """Calculate hash fingerprint for repository cache."""
        return hashlib.sha256(self.url).hexdigest()

    def get_current_commit(self):
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
            repodir = tempfile.mkdtemp(dir=os.path.join(repocachedir, 'incoming'))

        if repodir is None:
            repodir = tempfile.mkdtemp(dir=self.args.outdir)
            self.task.cleanup_dirs.append(repodir)

        # special case when using osc and creating an obscpio, use current work
        # directory to allow the developer to work inside of the git repo and fetch
        # local changes
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
        self.clone_dir = os.path.abspath(os.path.join(self.repodir, basename))
        logging.debug("CLONE_DIR: %s"%self.clone_dir)

    def is_sslverify_enabled(self):
	"""Returns ``True`` if the ``sslverify`` option has been enabled or
	not been set (default enabled) ``False`` otherwise."""
	return 'sslverify' not in self.args.__dict__ or self.args.__dict__['sslverify']

    def version_iso_cleanup(self, version):
        """Reformat timestamp value."""
        version = re.sub(r'([0-9]{4})-([0-9]{2})-([0-9]{2}) +'
                         r'([0-9]{2})([:]([0-9]{2})([:]([0-9]{2}))?)?'
                         r'( +[-+][0-9]{3,4})', r'\1\2\3T\4\6\8', version)
        version = re.sub(r'[-:]', '', version)
        return version

    def prep_tree_for_archive(self, subdir, outdir, dstname):
        """Prepare directory tree for creation of the archive by copying the
        requested sub-directory to the top-level destination directory.
        """
        src = os.path.join(self.clone_dir, subdir)
        if not os.path.exists(src):
            raise Exception("%s: No such file or directory" % src)

        dst = os.path.join(outdir, dstname)
        if os.path.exists(dst) and \
            (os.path.samefile(src, dst) or
             os.path.samefile(os.path.dirname(src), dst)):
            raise Exception("%s: src and dst refer to same file" % src)

        shutil.copytree(src, dst, symlinks=True)

	self.arch_dir = dst
