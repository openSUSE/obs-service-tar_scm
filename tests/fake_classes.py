class FakeCli(dict):  # pylint: disable=no-init,too-few-public-methods
    def __init__(self, match_tag=False):
        self.url                = ''
        self.revision           = ''
        self.changesgenerate    = False
        self.subdir             = ''
        self.match_tag          = match_tag
        self.user               = ''
        self.keyring_passphrase = ''


class FakeTasks():  # pylint: disable=no-init,too-few-public-methods
    pass


class FakeSCM():
    def __init__(self, version):
        self.version = version

    # pylint: disable=unused-argument,no-self-use,no-init,
    # pylint: disable=too-few-public-methods
    def detect_version(self, args):
        return self.version
