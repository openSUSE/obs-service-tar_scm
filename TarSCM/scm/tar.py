import glob
import os
import sys
from base import scm


class tar(scm):
    def fetch_upstream(self, clone_dir, cwd, kwargs):
        """SCM specific version of fetch_uptream for tar."""
        if kwargs.obsinfo is None:
            files = glob.glob('*.obsinfo')
            if len(files) > 0:
                # or we refactor and loop about all on future
                kwargs.obsinfo = files[0]
        if kwargs.obsinfo is None:
            sys.exit("ERROR: no .obsinfo file found")
        basename = clone_dir = self.read_from_obsinfo(kwargs.obsinfo, "name")
        clone_dir += "-" + self.read_from_obsinfo(kwargs.obsinfo, "version")
        if not os.path.exists(clone_dir):
            # not need in case of local osc build
            os.rename(basename, clone_dir)

        return clone_dir

    def update_cache(self, clone_dir):
        """Update sources via tar."""
        pass

    def detect_version(self, args, repodir):
        """Read former stored version."""
        return self.read_from_obsinfo(args['obsinfo'], "version")

    def get_timestamp(self, args, repodir):
        return int(self.read_from_obsinfo(args.obsinfo, "mtime"))

    def read_from_obsinfo(self, filename, key):
        infofile = open(filename, "r")
        line = infofile.readline()
        while line:
            k = line.split(":", 1)
            if k[0] == key:
                return k[1].strip()
            line = infofile.readline()
        return ""
