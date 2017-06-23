'''
This module contains the class tasks
'''

import glob
import copy
import atexit
import logging
import os
import shutil
import sys
import re

import TarSCM.scm
import TarSCM.archive
from TarSCM.helpers import Helpers
from TarSCM.changes import Changes
from TarSCM.exceptions import OptionsError
import yaml


class Tasks():
    '''
    Class to create a task list for formats which can contain more then one scm
    job like snapcraft or appimage
    '''
    def __init__(self):
        self.task_list      = []
        self.cleanup_dirs   = []
        self.helpers        = Helpers()
        self.changes        = Changes()
        self.scm_object     = None
        self.data_map       = None

    def cleanup(self):
        """Cleaning temporary directories."""
        logging.debug("Cleaning: %s", ' '.join(self.cleanup_dirs))

        for dirname in self.cleanup_dirs:
            if not os.path.exists(dirname):
                continue
            shutil.rmtree(dirname)
        self.cleanup_dirs = []
        # Unlock to prevent dead lock in cachedir if exception
        # gets raised
        if self.scm_object:
            self.scm_object.unlock_cache()

    def generate_list(self, args):
        '''
        Generate list of scm jobs from appimage.yml, snapcraft.yml or a single
        job from cli arguments.
        '''
        scms = ['git', 'tar', 'svn', 'bzr', 'hg']

        if args.appimage:
            # we read the SCM config from appimage.yml
            filehandle = open('appimage.yml')
            self.data_map = yaml.safe_load(filehandle)
            filehandle.close()
            args.use_obs_scm = True
            build_scms = ()
            try:
                build_scms = self.data_map['build'].keys()
            except TypeError:
                pass
            # run for each scm an own task
            for scm in scms:
                if scm not in build_scms:
                    continue
                for url in self.data_map['build'][scm]:
                    args.url = url
                    args.scm = scm
                    self.task_list.append(copy.copy(args))

        elif args.snapcraft:
            # we read the SCM config from snapcraft.yaml instead
            # getting it via parameters
            filehandle = open('snapcraft.yaml')
            self.data_map = yaml.safe_load(filehandle)
            filehandle.close()
            args.use_obs_scm = True
            # run for each part an own task
            for part in self.data_map['parts'].keys():
                args.filename = part
                if 'source-type' not in self.data_map['parts'][part].keys():
                    continue
                pep8_1 = self.data_map['parts'][part]['source-type']
                if pep8_1 not in scms:
                    continue
                # avoid conflicts with files
                args.clone_prefix = "_obs_"
                args.url = self.data_map['parts'][part]['source']
                self.data_map['parts'][part]['source'] = part
                args.scm = self.data_map['parts'][part]['source-type']
                del self.data_map['parts'][part]['source-type']
                self.task_list.append(copy.copy(args))

        else:
            self.task_list.append(args)

    def process_list(self):
        '''
        process tasks from the task_list
        '''
        for task in self.task_list:
            self.process_single_task(task)

    def finalize(self, args):
        '''
        final steps after processing task list
        '''
        if args.snapcraft:
            # write the new snapcraft.yaml file
            # we prefix our own here to be sure to not overwrite user files,
            # if he is using us in "disabled" mode
            new_file = args.outdir + '/_service:snapcraft:snapcraft.yaml'
            with open(new_file, 'w') as outfile:
                outfile.write(yaml.dump(self.data_map,
                                        default_flow_style=False))

    def process_single_task(self, args):
        '''
        do the work for a single task
        '''
        logging.basicConfig(format="%(message)s", stream=sys.stderr,
                            level=logging.INFO)
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)

        # force cleaning of our workspace on exit
        atexit.register(self.cleanup)

        scm2class = {
            'git': 'git',
            'bzr': 'Bzr',
            'hg':  'hg',
            'svn': 'svn',
            'tar': 'tar',
        }

        # create objects for TarSCM.<scm> and TarSCM.helpers
        try:
            scm_class = getattr(TarSCM.scm, scm2class[args.scm])
        except:
            raise OptionsError("Please specify valid --scm=... options")

        # self.scm_object is need to unlock cache in cleanup
        # if exception occurs
        self.scm_object = scm_object   = scm_class(args, self)

        scm_object.fetch_upstream()

        if args.filename:
            dstname = basename = args.filename
        else:
            dstname = basename = os.path.basename(scm_object.clone_dir)

        version = self.get_version(scm_object, args)
        changesversion = version
        if version and not sys.argv[0].endswith("/tar") \
           and not sys.argv[0].endswith("/snapcraft") \
           and not sys.argv[0].endswith("/appimage"):
            dstname += '-' + version

        logging.debug("DST: %s", dstname)

        detected_changes = scm_object.detect_changes()

        scm_object.prep_tree_for_archive(args.subdir, args.outdir,
                                         dstname=dstname)
        self.cleanup_dirs.append(scm_object.arch_dir)

        if args.use_obs_scm:
            arch = TarSCM.archive.ObsCpio()
        else:
            arch = TarSCM.archive.Tar()

        arch.extract_from_archive(scm_object.arch_dir, args.extract,
                                  args.outdir)

        arch.create_archive(
            scm_object,
            basename  = basename,
            dstname   = dstname,
            version   = version,
            cli       = args
        )

        if detected_changes:
            changesauthor = self.changes.get_changesauthor(args)

            logging.debug("AUTHOR: %s", changesauthor)

            if not version:
                args.version = "_auto_"
                changesversion = self.get_version(scm_object, args)

            for filename in glob.glob('*.changes'):
                new_changes_file = os.path.join(args.outdir, filename)
                shutil.copy(filename, new_changes_file)
                self.changes.write_changes(new_changes_file,
                                           detected_changes['lines'],
                                           changesversion, changesauthor)
            self.changes.write_changes_revision(args.url, args.outdir,
                                                detected_changes['revision'])

        scm_object.finalize()

    def get_version(self, scm_object, args):
        '''
        Generate final version number by detecting version from scm if not
        given as cli option and applying versionrewrite_pattern and
        versionprefix if given as cli option
        '''
        version = args.version
        if version == '_none_':
            return ''
        if version == '_auto_' or args.versionformat:
            version = self.detect_version(scm_object, args)
        if args.versionrewrite_pattern:
            regex = re.compile(args.versionrewrite_pattern)
            version = regex.sub(args.versionrewrite_replacement, version)
        if args.versionprefix:
            version = "%s.%s" % (args.versionprefix, version)

        logging.debug("VERSION(auto): %s", version)
        return version

    def detect_version(self, scm_object, args):
        """Automatic detection of version number for checked-out repository."""

        version = scm_object.detect_version(args.__dict__).strip()
        logging.debug("VERSION(auto): %s", version)
        return version
