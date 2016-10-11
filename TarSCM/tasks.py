import glob
import copy 
import atexit
import logging
import os
import shutil
import sys
import re

import scm
from archive import archive
from helpers import helpers
from changes import changes
from exceptions import OptionsError
import yaml


class tasks():
    def __init__(self):
        self.task_list      = []
        self.cleanup_dirs   = []
        self.helpers        = helpers()
        self.changes        = changes()

    def cleanup(self):
        """Cleaning temporary directories."""
        logging.debug("Cleaning: %s", ' '.join(self.cleanup_dirs))

        for d in self.cleanup_dirs:
            if not os.path.exists(d):
                continue
            shutil.rmtree(d)

    def generate_list(self,args):

        if  args.snapcraft:
            # we read the SCM config from snapcraft.yaml instead from _service file
            f = open('snapcraft.yaml')
            self.dataMap = yaml.safe_load(f)
            f.close()
            args.use_obs_scm = True
            # run for each part an own task
            for part in self.dataMap['parts'].keys():
                args.filename = part
                if 'source-type' not in self.dataMap['parts'][part].keys():
                    continue
                pep8_1 = self.dataMap['parts'][part]['source-type']
                pep8_2 = ['git','tar','svn','bzr','hg']
                if pep8_1 not in pep8_2:
                    continue
                # avoid conflicts with files
                args.clone_prefix = "_obs_"
                args.url = self.dataMap['parts'][part]['source']
                self.dataMap['parts'][part]['source'] = part
                args.scm = self.dataMap['parts'][part]['source-type']
                del self.dataMap['parts'][part]['source-type']
                self.task_list.append(copy.copy(args))

        else:
            self.task_list.append(args)

    def process_list(self):
        for task in self.task_list:
            self._process_single_task(task)

    def finalize(self,args):
        if  args.snapcraft:
            # write the new snapcraft.yaml file
            # we prefix our own here to be sure to not overwrite user files, if he
            # is using us in "disabled" mode
            new_file = args.outdir + '/_service:snapcraft:snapcraft.yaml'
            with open(new_file, 'w') as outfile:
                outfile.write(yaml.dump(self.dataMap, default_flow_style=False))

    def _process_single_task(self,args):
        FORMAT  = "%(message)s"
        logging.basicConfig(format=FORMAT, stream=sys.stderr, level=logging.INFO)
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)

        # force cleaning of our workspace on exit
        atexit.register(self.cleanup)

        # create objects for TarSCM.<scm> and TarSCM.helpers
        try:
            scm_class    = getattr(scm, args.scm)
        except:
            raise OptionsError("Please specify valid --scm=... options")
        scm_object   = scm_class(args, self)
        helpers      = scm_object.helpers

        repocachedir = scm_object.get_repocachedir()

        repodir      = scm_object.repodir

        scm_object.fetch_upstream()

        if args.filename:
            dstname = basename = args.filename
        else:
            dstname = basename = os.path.basename(scm_object.clone_dir)

        version = self.get_version(scm_object, args)
        changesversion = version
        if version and not sys.argv[0].endswith("/tar") \
           and not sys.argv[0].endswith("/snapcraft"):
            dstname += '-' + version

        logging.debug("DST: %s", dstname)

        changes = scm_object.detect_changes()

        scm_object.prep_tree_for_archive(args.subdir, args.outdir, dstname=dstname)
        self.cleanup_dirs.append(scm_object.arch_dir)

        arch = archive()

        arch.extract_from_archive(scm_object.arch_dir, args.extract, args.outdir)

        # FIXME: Consolidate calling parameters and shrink to one call of create_archive
        if args.use_obs_scm:
            tmp_archive = archive.obscpio()
            tmp_archive.create_archive(
                    scm_object,
                    basename,
                    dstname,
                    version,
                    scm_object.get_current_commit(scm_object.clone_dir),
                    args)
        else:
            tmp_archive = archive.tar()
            tmp_archive.create_archive(
                    scm_object,
                    args.outdir,
                    dstname=dstname,
                    extension=args.extension,
                    exclude=args.exclude,
                    include=args.include,
                    package_metadata=args.package_meta,
                    timestamp=self.helpers.get_timestamp(scm_object, args, scm_object.clone_dir))

        if changes:
            changesauthor = self.changes.get_changesauthor(args)

            logging.debug("AUTHOR: %s", changesauthor)

            if not version:
                args.version = "_auto_"
                changesversion = self.get_version(scm_object, args)

            for filename in glob.glob('*.changes'):
                new_changes_file = os.path.join(args.outdir, filename)
                shutil.copy(filename, new_changes_file)
                self.changes.write_changes(new_changes_file, changes['lines'],
                              changesversion, changesauthor)
            self.changes.write_changes_revision(args.url, args.outdir,
                                   changes['revision'])

        # Populate cache
        logging.debug("Using repocachedir: '%s'" % repocachedir)
        if repocachedir and os.path.isdir(os.path.join(repocachedir, 'repo')):
            repodir2 = os.path.join(repocachedir, 'repo', scm_object.repohash)
            if repodir2 and not os.path.isdir(repodir2):
                os.rename(repodir, repodir2)
            elif not os.path.samefile(repodir, repodir2):
                self.cleanup_dirs.append(repodir)

    def get_version(self, scm_object, args):
        version = args.version
        if version == '_auto_' or args.versionformat:
            version = self.detect_version(scm_object, args)
        if args.versionprefix:
            version = "%s.%s" % (args.versionprefix, version)

        logging.debug("VERSION(auto): %s", version)
        return version

    def detect_version(self, scm_object, args):
        """Automatic detection of version number for checked-out repository."""

        version = scm_object.detect_version(args.__dict__).strip()
        logging.debug("VERSION(auto): %s", version)
        return version
