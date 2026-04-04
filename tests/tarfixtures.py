#!/usr/bin/env python

from typing import Any
from tests.fixtures import Fixtures


class TarFixtures(Fixtures):

    """Methods to create and populate a tar directory.

    tar tests use this class in order to have something to test against.
    """

    def init(self) -> Any:
        pass

    def run(self, cmd: Any) -> Any:
        pass
