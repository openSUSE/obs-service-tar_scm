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
        if self.args.obsinfo is None:
            raise SystemExit("ERROR: no .obsinfo file found in directory: "
                             "'%s'" % os.getcwd())
        self.basename  = self.read_from_obsinfo(self.args.obsinfo, "name")
        self.clone_dir = self.read_from_obsinfo(self.args.obsinfo, "scmdir")
        # for backwards compatibility - where scmdir is not set
        if not self.clone_dir:
            self.clone_dir = self.basename
        if "/" in self.clone_dir:
            sys.exit("name in obsinfo contains '/'.")

        version = self.read_from_obsinfo(self.args.obsinfo, "version")

        if "/" in version or '..' in version:
            sys.exit("verion in obsinfo contains '/' or '..'.")

        self.basename += "-" + version

        if not os.path.exists(self.clone_dir):
            self._final_rename_needed = True
            # not need in case of local osc build
            try:
                os.rename(self.clone_dir, self.basename)
            except OSError:
                raise SystemExit(
                    "Error while moving from '%s' to '%s'\n"
                    "Current working directory: '%s'" %
                    (self.clone_dir, self.basename, os.getcwd())
                )

    def update_cache(self):
        """Update sources via tar."""
        pass

    def detect_version(self, args):
        """Read former stored version."""
        return self.read_from_obsinfo(self.args.obsinfo, "version")

    def get_timestamp(self):
        return int(self.read_from_obsinfo(self.args.obsinfo, "mtime"))

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
