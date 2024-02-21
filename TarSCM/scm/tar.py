import glob
import os
import sys

from TarSCM.scm.base import Scm


class Tar(Scm):
    scm = 'tar'

    def fetch_upstream(self):
        """SCM specific version of fetch_upstream for tar."""
        if self.args.obsinfo is None:
            files = glob.glob('*.obsinfo')
            if files:
                # or we refactor and loop about all on future
                self.args.obsinfo = files[0]

        version = None
        if self.args.obsinfo:
            self.basename = self.clone_dir = self.read_from_obsinfo(
                self.args.obsinfo, "name"
            )
            version = self.read_from_obsinfo(self.args.obsinfo, "version")

        if self.args.filename:
            self.basename = self.clone_dir = self.args.filename

        if self.args.version and self.args.version != '_auto_':
            version = self.args.version

        if not self.basename or not self.clone_dir:
            raise SystemExit("ERROR: no .obsinfo file found in directory\n"
                             "       and no manual configuration: "
                             "'%s'" % os.getcwd())
        if "/" in self.clone_dir:
            sys.exit("name in obsinfo contains '/'.")

        if "/" in version or '..' in version:
            raise SystemExit("version in obsinfo contains '/' or '..'.")

        if version != '' and version != '_none_':
            self.clone_dir += "-" + version

        if not os.path.exists(self.clone_dir) \
                and self.basename != self.clone_dir:
            self._final_rename_needed = True
            # not need in case of local osc build
            try:
                os.rename(self.basename, self.clone_dir)
            except OSError:
                raise SystemExit(
                    "Error while moving from '%s' to '%s'\n"
                    "Current working directory: '%s'" %
                    (self.basename, self.clone_dir, os.getcwd())
                )

    def update_cache(self):
        """Update sources via tar."""
        pass

    def detect_version(self, args):
        """Read former stored version."""
        if self.args.obsinfo:
            return self.read_from_obsinfo(self.args.obsinfo, "version")

    def get_timestamp(self):
        if self.args.obsinfo:
            return int(self.read_from_obsinfo(self.args.obsinfo, "mtime"))
        if self.args.filename:
            return int(os.path.getmtime(self.args.filename))

    def read_from_obsinfo(self, filename, key):
        infofile = open(filename, "r")
        line = infofile.readline()
        while line:
            k = line.split(":", 1)
            if k[0] == key:
                return k[1].strip()
            line = infofile.readline()
        return ""

    def finalize(self):
        """Execute final cleanup of workspace"""
        if self._final_rename_needed:
            os.rename(self.clone_dir, self.basename)

    # no cleanup is necessary for tar
    def cleanup(self):
        pass
