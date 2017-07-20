import fnmatch
import os
import re
import subprocess
import sys
import tarfile
import shutil
import logging
import tempfile

from TarSCM.helpers import Helpers

try:
    from io import StringIO
except:
    from StringIO import StringIO

METADATA_PATTERN = re.compile(r'.*/\.(bzr|git(ignore)?|hg|svn)(\/.*|$)')


class BaseArchive():
    def __init__(self):
        self.helpers        = Helpers()
        self.archivefile    = None
        self.metafile       = None

    def extract_from_archive(self, repodir, files, outdir):
        """Extract all files directly outside of the archive.
        """
        if files is None:
            return

        for filename in files:
            src = os.path.join(repodir, filename)
            if not os.path.exists(src):
                sys.exit("%s: No such file or directory" % src)

            if shutil.copy(src, outdir):
                sys.exit("%s: Failed to copy file" % src)


class ObsCpio(BaseArchive):
    def create_archive(self, scm_object, **kwargs):
        """Create an OBS cpio archive of repodir in destination directory.
        """
        basename = kwargs['basename']
        dstname  = kwargs['dstname']
        version  = kwargs['version']
        args     = kwargs['cli']
        commit   = scm_object.get_current_commit()

        (workdir, topdir) = os.path.split(scm_object.arch_dir)
        extension = 'obscpio'

        cwd = os.getcwd()
        os.chdir(workdir)

        archivefilename = os.path.join(args.outdir, dstname + '.' + extension)
        archivefile     = open(archivefilename, "w")
        proc            = subprocess.Popen(
            ['cpio', '--create', '--format=newc'],
            shell  = False,
            stdin  = subprocess.PIPE,
            stdout = archivefile,
            stderr = subprocess.STDOUT
        )

        # transform glob patterns to regular expressions
        includes = r'|'.join([fnmatch.translate(x) for x in args.include])
        excl_arr = [fnmatch.translate(x) for x in args.exclude]
        excludes = r'|'.join(excl_arr) or r'$.'

        # add topdir without filtering for now
        for root, dirs, files in os.walk(topdir, topdown=False):
            # excludes
            dirs[:] = [os.path.join(root, d) for d in dirs]
            dirs[:] = [d for d in dirs if not re.match(excludes, d)]

            # exclude/include files
            files = [os.path.join(root, f) for f in files]
            files = [f for f in files if not re.match(excludes, f)]
            files = [f for f in files if re.match(includes, f)]

            for name in dirs:
                if not METADATA_PATTERN.match(name):
                    proc.stdin.write(name)
                    proc.stdin.write("\n")

            for name in files:
                if not METADATA_PATTERN.match(name):
                    proc.stdin.write(name)
                    proc.stdin.write("\n")

        proc.stdin.close()
        ret_code = proc.wait()
        if ret_code != 0:
            raise SystemExit("Creating the cpio archive failed!")
        archivefile.close()

        # write meta data
        metafile = open(os.path.join(args.outdir, basename + '.obsinfo'), "w")
        metafile.write("name: " + basename + "\n")
        metafile.write("version: " + version + "\n")
        tstamp = self.helpers.get_timestamp(scm_object, args, topdir)
        metafile.write("mtime: " + str(tstamp) + "\n")

        if commit:
            metafile.write("commit: " + commit + "\n")

        metafile.close()

        self.archivefile    = archivefile.name
        self.metafile       = metafile.name
        os.chdir(cwd)


class Tar(BaseArchive):
    def create_archive(self, scm_object, **kwargs):
        """Create a tarball of repodir in destination directory."""
        (workdir, topdir) = os.path.split(scm_object.arch_dir)

        args                = kwargs['cli']
        outdir              = args.outdir
        dstname             = kwargs['dstname']
        extension           = (args.extension or 'tar')
        exclude             = args.exclude
        include             = args.include
        package_metadata    = args.package_meta
        timestamp           = self.helpers.get_timestamp(
            scm_object,
            args,
            scm_object.clone_dir
        )

        incl_patterns = []
        excl_patterns = []
        for i in include:
            # for backward compatibility add a trailing '*' if i isn't a
            # pattern
            if fnmatch.translate(i) == i + fnmatch.translate(r''):
                i += r'*'

            pat = fnmatch.translate(os.path.join(topdir, i))
            incl_patterns.append(re.compile(pat))

        for exc in exclude:
            pat = fnmatch.translate(os.path.join(topdir, exc))
            excl_patterns.append(re.compile(pat))

        def tar_exclude(filename):
            """
            Exclude (return True) or add (return False) file to tar achive.
            """
            if not package_metadata and METADATA_PATTERN.match(filename):
                return True

            if incl_patterns:
                for pat in incl_patterns:
                    if pat.match(filename):
                        return False
                return True

            for pat in excl_patterns:
                if pat.match(filename):
                    return True
            return False

        def reset(tarinfo):
            """Python 2.7 only: reset uid/gid to 0/0 (root)."""
            tarinfo.uid = tarinfo.gid = 0
            tarinfo.uname = tarinfo.gname = "root"
            if timestamp != 0:
                tarinfo.mtime = timestamp
            return tarinfo

        def tar_filter(tarinfo):
            if tar_exclude(tarinfo.name):
                return None

            return reset(tarinfo)

        cwd = os.getcwd()
        os.chdir(workdir)

        tar = tarfile.open(
            os.path.join(outdir, dstname + '.' + extension),
            "w"
        )
        try:
            tar.add(topdir, recursive=False, filter=reset)
        except TypeError:
            # Python 2.6 compatibility
            tar.add(topdir, recursive=False)
        for entry in map(lambda x: os.path.join(topdir, x),
                         sorted(os.listdir(topdir))):
            try:
                tar.add(entry, filter=tar_filter)
            except TypeError:
                # Python 2.6 compatibility
                tar.add(entry, exclude=tar_exclude)
        tar.close()

        self.archivefile    = tar.name

        os.chdir(cwd)


class Gbp(BaseArchive):

    def create_archive(self, scm_object, **kwargs):
        """Create Debian source artefacts using git-buildpackage.
        """
        args = kwargs['cli']
        version = kwargs['version']

        (workdir, topdir) = os.path.split(scm_object.clone_dir)

        cwd = os.getcwd()
        os.chdir(workdir)

        if not args.revision:
            revision = 'origin/master'
        else:
            revision = 'origin/' + args.revision

        command = ['gbp', 'buildpackage', '--git-notify=off',
                   '--git-force-create', '--git-cleaner="true"']

        # we are not on a proper local branch due to using git-reset but we
        # anyway use the --git-export option
        command.extend(['--git-ignore-branch',
                        "--git-export=%s" % revision])

        # gbp can load submodules without having to run the git command, and
        # will ignore submodules even if loaded manually unless this option is
        # passed.
        if args.submodules:
            command.extend(['--git-submodules'])

        # create local pristine-tar branch if present
        ret, output = self.helpers.run_cmd(['git', 'rev-parse', '--verify',
                                            '--quiet', 'origin/pristine-tar'],
                                           cwd=scm_object.clone_dir)
        if not ret:
            ret, output = self.helpers.run_cmd(['git', 'update-ref',
                                                'refs/heads/pristine-tar',
                                                'origin/pristine-tar'],
                                               cwd=scm_object.clone_dir)
            if not ret:
                command.append('--git-pristine-tar')
            else:
                command.append('--git-no-pristine-tar')
        else:
            command.append('--git-no-pristine-tar')

        # Prevent potentially dangerous arguments from being passed to gbp,
        # e.g. via cleaner, postexport or other hooks.
        if args.gbp_build_args:
            build_args = args.gbp_build_args.split(' ')
            safe_args = re.compile(
                '--git-verbose|--git-upstream-tree=.*|--git-no-pristine-tar')
            p = re.compile('--git-.*|--hook-.*|--.*-hook=.*')

            gbp_args = [arg for arg in build_args if safe_args.match(arg)]
            dpkg_args = [arg for arg in build_args if not p.match(arg)]

            ignored_args = list(set(build_args) - set(gbp_args + dpkg_args))
            if ignored_args:
                logging.info("Ignoring build_args: %s" % ignored_args)
            command.extend(gbp_args + dpkg_args)

        # Set the version in the changelog. Note that we can't simply use
        # --source-option=-Dversion=$ver as it will not change the tarball
        # name, which means dpkg-source -x pkg.dsc will fail as the names
        # and version will not match
        cl_path = os.path.join(scm_object.clone_dir, 'debian', 'changelog')
        if (os.path.isfile(cl_path) and
                version not in ['', '_none_', '_auto_', None]):
            # Some characters are legal in Debian's versions but not in a git
            # tag, so they get substituted
            version = re.sub(r'_', r'~', version)
            version = re.sub(r'%', r':', version)
            with open(cl_path, 'r') as cl:
                lines = cl.readlines()
            # non-native packages MUST have a debian revision (-xyz)
            if (re.search(r'-', lines[0]) is not None and
                    re.search(r'-', version)) is None:
                logging.warning("Package is non-native but requested version"
                                " %s is native! Ignoring.", version)
            else:
                with open(cl_path, 'w+') as cl:
                    # A valid debian changelog has 'package (version) release'
                    # as the first line, if it's malformed we don't care as it
                    # will not even build
                    logging.debug("Setting version to %s", version)
                    # gbp by default complains about uncommitted changes
                    command.append("--git-ignore-new")
                    lines[0] = re.sub(r'^(.+) \(.+\) (.+)',
                                      r'\1 (%s) \2' % version, lines[0])
                    cl.write("".join(lines))

        logging.debug("Running in %s", scm_object.clone_dir)

        self.helpers.safe_run(command, cwd=scm_object.clone_dir)

        # Use dpkg to find out what source artefacts have been built and copy
        # them back, which allows the script to be future-proof and work with
        # all present and future package formats
        sources = self.helpers.safe_run(['dpkg-scansources', workdir],
                                        cwd=workdir)[1]

        FILES_PATTERN = re.compile(
            r'^Files:(.*(?:\n .*)+)', flags=re.MULTILINE)
        for match in FILES_PATTERN.findall(sources):
            logging.info("Files:")
            for line in match.strip().split("\n"):
                fname = line.strip().split(' ')[2]
                logging.info(" %s", fname)
                input_file = os.path.join(workdir, fname)
                output_file = os.path.join(args.outdir, fname)

                if (args.gbp_dch_release_update and
                        fnmatch.fnmatch(fname, '*.dsc')):
                    # This tag is used by the build-recipe-dsc to set the OBS
                    # revision: https://github.com/openSUSE/obs-build/pull/192
                    logging.debug("Setting OBS-DCH-RELEASE in %s", input_file)
                    with open(input_file, "a") as dsc_file:
                        dsc_file.write("OBS-DCH-RELEASE: 1")

                shutil.copy(input_file, output_file)

        os.chdir(cwd)
