import glob
import os
from TarSCM.scm.base import scm


class tar(scm):
    def fetch_upstream(self):
        """SCM specific version of fetch_uptream for tar."""
        if self.args.obsinfo is None:
            files = glob.glob('*.obsinfo')
            if len(files) > 0:
                # or we refactor and loop about all on future
                self.args.obsinfo = files[0]
        if self.args.obsinfo is None:
            raise SystemExit("ERROR: no .obsinfo file found in directory: "
                             "'%s'" % os.getcwd())
        self.basename = self.clone_dir = self.read_from_obsinfo(
            self.args.obsinfo,
            "name"
        )
        self.clone_dir += "-" + self.read_from_obsinfo(self.args.obsinfo,
                                                       "version")
        if not os.path.exists(self.clone_dir):
            self.final_rename_needed = 1
            # not need in case of local osc build
            try:
                os.rename(self.basename, self.clone_dir)
            except OSError as e:
                raise SystemExit(
                    "Error while moving from '%s' to '%s')\n"
                    "Current working directory: '%s'" %
                    (self.basename, self.clone_dir, os.getcwd())
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
        if self.final_rename_needed:
            os.rename(self.clone_dir, self.basename)
