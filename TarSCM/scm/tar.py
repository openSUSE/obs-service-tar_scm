from base import scm

class tar(scm):
    def fetch_upstream(self):
        """SCM specific version of fetch_uptream for tar."""
        if self.args.obsinfo is None:
            files = glob.glob('*.obsinfo')
            if len(files) > 0:
                # or we refactor and loop about all on future
                self.args.obsinfo = files[0]
        if self.args.obsinfo is None:
            sys.exit("ERROR: no .obsinfo file found")
        basename = self.clone_dir = self.read_from_obsinfo(args.obsinfo, "name")
        self.clone_dir += "-" + self.read_from_obsinfo(args.obsinfo, "version")
        if not os.path.exists(self.clone_dir):
            # not need in case of local osc build
            os.rename(basename, self.clone_dir)

    def update_cache(self):
        """Update sources via tar."""
        pass

    def detect_version(self,args):
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

