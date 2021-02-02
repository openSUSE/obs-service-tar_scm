class FakeCli(dict):  # pylint: disable=no-init,too-few-public-methods
    def __init__(self, match_tag=False):
        self.url                = ''
        self.revision           = ''
        self.changesgenerate    = False
        self.subdir             = ''
        self.match_tag          = match_tag
        self.user               = ''
        self.keyring_passphrase = ''
        self.maintainers_asc = None


class FakeTasks():  # pylint: disable=no-init,too-few-public-methods
    pass


class FakeSCM():
    def __init__(self, version):
        self.version = version
        self.maintainers_asc = None

    # pylint: disable=unused-argument,no-self-use,no-init,
    # pylint: disable=too-few-public-methods
    def detect_version(self, args):
        return self.version

    def version_iso_cleanup(self, version, debian):
        return self.version
