# -*- coding: utf-8 -*-
from typing import Any
class FakeCli(dict):  # pylint: disable=no-init,too-few-public-methods
    url                = ''
    revision           = ''
    changesgenerate    = False
    subdir             = ''
    user               = ''
    keyring_passphrase = ''
    maintainers_asc = None
    def __init__(self, match_tag: Any=False) -> None:
        super(FakeCli, self).__init__()
        self.match_tag          = match_tag


class FakeTasks():  # pylint: disable=no-init,too-few-public-methods
    pass


class FakeSCM():
    def __init__(self, version: Any) -> None:
        self.version = version
        self.maintainers_asc = None

    # pylint: disable=unused-argument,no-self-use,no-init,
    # pylint: disable=too-few-public-methods
    def detect_version(self, args: Any) -> Any:
        return self.version

    def version_iso_cleanup(self, version: Any, debian: Any) -> Any:
        return self.version
