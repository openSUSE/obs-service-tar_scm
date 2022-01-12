'''
This module contains the class tasks
'''
from __future__ import print_function

import glob
import copy
import atexit
import logging
import os
import shutil
import sys
import re
import locale
import json
import io
import yaml

import TarSCM.scm
import TarSCM.archive
from TarSCM.helpers import Helpers, file_write_legacy
from TarSCM.changes import Changes
from TarSCM.exceptions import OptionsError


class Tasks():
    '''
    Class to create a task list for formats which can contain more then one scm
    job like snapcraft or appimage
    '''
    def __init__(self, args):
        self.task_list      = []
        self.cleanup_dirs   = []
        self.helpers        = Helpers()
        self.changes        = Changes()
        self.scm_object     = None
        self.data_map       = None
        self.args           = args

    def cleanup(self):
        """Cleaning temporary directories."""
        if self.args.skip_cleanup:
            logging.debug("Skipping cleanup")
            return

        logging.debug("Cleaning: %s", ' '.join(self.cleanup_dirs))

        for dirname in self.cleanup_dirs:
            if not os.path.exists(dirname):
                continue
            ploc = locale.getpreferredencoding()
            shutil.rmtree(dirname.encode(ploc))
        self.cleanup_dirs = []
        # Unlock to prevent dead lock in cachedir if exception
        # gets raised
        if self.scm_object:
            self.scm_object.unlock_cache()
            # calls the corresponding cleanup routine
            self.scm_object.cleanup()

    def generate_list(self):
        '''
        Generate list of scm jobs from appimage.yml, snapcraft.yaml or a single
        job from cli arguments.
        '''
        args = self.args
        scms = ['git', 'tar', 'svn', 'bzr', 'hg']

        if args.appimage:
            # we read the SCM config from appimage.yml
            with io.open('appimage.yml', encoding='utf-8') as filehandle:
                self.data_map = yaml.safe_load(filehandle)
            args.use_obs_scm = True
            build_scms = ()
            try:
                build_scms = self.data_map['build'].keys()
            except (TypeError, KeyError):
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
            with io.open('snapcraft.yaml', encoding='utf-8') as filehandle:
                self.data_map = yaml.safe_load(filehandle)
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

    def finalize(self):
        '''
        final steps after processing task list
        '''
        args = self.args
        if args.snapcraft:
            # write the new snapcraft.yaml file
            # we prefix our own here to be sure to not overwrite user files,
            # if he is using us in "disabled" mode
            new_file = args.outdir + '/_service:snapcraft:snapcraft.yaml'
            yml_str = yaml.dump(self.data_map, default_flow_style=False)
            file_write_legacy(new_file, yml_str)

        # execute also download_files for downloading single sources
        if args.snapcraft or args.appimage:
            download_files = '/usr/lib/obs/service/download_files'
            if os.path.exists(download_files):
                cmd = [download_files, '--outdir', args.outdir]
                rcode, output = self.helpers.run_cmd(cmd, None)

                if rcode != 0:
                    raise RuntimeError("download_files has failed:%s" % output)

    def check_for_branch_request(self):
        # we may have a _branch_request file. In that case we life in a
        # branch create by a webhook from github or gitlab pull/merge request
        # the source supposed to be merged is more important then the code
        # referenced in the _service file.
        args = self.args
        if not os.path.exists('_branch_request'):
            return args

        # is it a branch request?
        with io.open("_branch_request", "r", encoding='utf-8') as ofh:
            dat = json.load(ofh)
        if dat.get('object_kind') == 'merge_request':
            # gitlab merge request
            args.url = dat['project']['http_url']
            rev = dat['object_attributes']['source']['default_branch']
            args.revision = rev
        elif dat.get('action') == 'opened':
            # github pull request
            args.url = "https://github.com/"
            args.url += dat['pull_request']['head']['repo']['full_name']
            args.revision = dat['pull_request']['head']['sha']

        return args

    def process_single_task(self, args):
        '''
        do the work for a single task
        '''
        self.args = self.check_for_branch_request()

        logging.basicConfig(format="%(message)s", stream=sys.stderr,
                            level=logging.INFO)

        # force cleaning of our workspace on exit
        atexit.register(self.cleanup)

        scm2class = {
            'git': 'Git',
            'bzr': 'Bzr',
            'hg':  'Hg',
            'svn': 'Svn',
            'tar': 'Tar',
        }

        # create objects for TarSCM.<scm> and TarSCM.helpers
        try:
            scm_class = getattr(TarSCM.scm, scm2class[args.scm])
        except:
            msg = "Please specify valid --scm=... options"
            raise OptionsError(msg)  # pylint: disable=E0012,W0707

        # self.scm_object is need to unlock cache in cleanup
        # if exception occurs
        self.scm_object = scm_object   = scm_class(args, self)

        tmode = bool(os.getenv('TAR_SCM_TESTMODE'))
        if not tmode and not scm_object.check_url():
            sys.exit("--url does not match remote repository")

        try:
            scm_object.check_scm()
        except OSError:
            print("Please install '%s'" % scm_object.scm)
            sys.exit(1)

        scm_object.fetch_upstream()
        version = self.get_version()

        (dstname, changesversion, basename) = self._dstname(scm_object,
                                                            version)

        logging.debug("DST: %s", dstname)

        detected_changes = scm_object.detect_changes()

        if not args.use_obs_gbp:
            scm_object.prep_tree_for_archive(args.subdir, args.outdir,
                                             dstname=dstname)
            self.cleanup_dirs.append(scm_object.arch_dir)

        # For the GBP service there is no copy in arch_dir, so use clone_dir
        # which has the same content
        extract_src = scm_object.arch_dir
        if args.use_obs_scm:
            arch = TarSCM.archive.ObsCpio()
        elif args.use_obs_gbp:
            arch = TarSCM.archive.Gbp()
            extract_src = scm_object.clone_dir
        else:
            arch = TarSCM.archive.Tar()

        arch.extract_from_archive(extract_src, args.extract,
                                  args.outdir)

        arch.create_archive(
            scm_object,
            basename  = basename,
            dstname   = dstname,
            version   = version,
            cli       = args
        )

        if detected_changes:
            self._process_changes(args,
                                  version,
                                  changesversion,
                                  detected_changes)

        scm_object.finalize()

    def _dstname(self, scm_object, version):
        args = self.args
        if args.filename:
            basename = dstname = args.filename
        else:
            basename = dstname = os.path.basename(scm_object.clone_dir)

        if version and not sys.argv[0].endswith("/tar") \
           and not sys.argv[0].endswith("/snapcraft") \
           and not sys.argv[0].endswith("/appimage"):
            if isinstance(dstname, bytes):
                version = version.encode('UTF-8')
            if not args.without_version:
                dstname += '-' + version
        return (dstname, version, basename)

    def _process_changes(self, args, ver, changesversion, detected_changes):
        changesauthor = self.changes.get_changesauthor(args)

        logging.debug("AUTHOR: %s", changesauthor)

        if not ver:
            args.version = "_auto_"
            changesversion = self.get_version()

        logging.debug("Searching for '*.changes' in %s", os.getcwd())
        for filename in glob.glob('*.changes'):
            new_changes_file = os.path.join(args.outdir, filename)
            shutil.copy(filename, new_changes_file)
            self.changes.write_changes(new_changes_file,
                                       detected_changes['lines'],
                                       changesversion, changesauthor)
        self.changes.write_changes_revision(args.url, args.outdir,
                                            detected_changes['revision'])

    def get_version(self):
        '''
        Generate final version number by detecting version from scm if not
        given as cli option and applying versionrewrite_pattern and
        versionprefix if given as cli option
        '''
        version = self.args.version
        if version == '_none_':
            return ''
        if version == '_auto_' or self.args.versionformat:
            version = self.detect_version()
        if self.args.versionrewrite_pattern:
            regex = re.compile(self.args.versionrewrite_pattern)
            version = regex.sub(self.args.versionrewrite_replacement, version)
        else:
            args = self.args.__dict__
            debian = args.get('use_obs_gbp', False)
            version = self.scm_object.version_iso_cleanup(version, debian)
        if self.args.versionprefix:
            version = "%s.%s" % (self.args.versionprefix, version)

        logging.debug("VERSION(auto): %s", version)
        return version

    def detect_version(self):
        """Automatic detection of version number for checked-out repository."""

        version = self.scm_object.detect_version(self.args.__dict__).strip()
        logging.debug("VERSION(auto): %s", version)
        return version
