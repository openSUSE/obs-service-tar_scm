import fnmatch
import os
import re
import subprocess
import sys
import tarfile
import shutil
import logging
from TarSCM.helpers import helpers

try:
    from io import StringIO
except:
    from StringIO import StringIO

METADATA_PATTERN = re.compile(r'.*/\.(bzr|git(ignore)?|hg|svn)(\/.*|$)')


class BaseArchive():
    def __init__(self):
        self.helpers        = helpers()
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


class obscpio(BaseArchive):
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
        ts = self.helpers.get_timestamp(scm_object, args, topdir)
        metafile.write("mtime: " + str(ts) + "\n")

        if commit:
            metafile.write("commit: " + commit + "\n")

        metafile.close()

        self.archivefile    = archivefile.name
        self.metafile       = metafile.name
        os.chdir(cwd)


class tar(BaseArchive):
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

        for e in exclude:
            pat = fnmatch.translate(os.path.join(topdir, e))
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
