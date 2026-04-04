import os
import logging
import re
import configparser
from io import StringIO
from typing import Any, List, Optional


class Config():
    # pylint: disable=too-few-public-methods
    def __init__(
            self,
            files: List[List[Any]]=[['/etc/obs/services/tar_scm', True]]
    ) -> None:
        try:
            rc_file = [
                os.path.join(os.environ['HOME'], '.obs', 'tar_scm'),
                True
            ]
            files.append(rc_file)
        except KeyError:
            pass

        self.configs            = []
        self.default_section    = 'tar_scm'
        # We're in test-mode, so don't let any local site-wide
        # or per-user config impact the test suite.
        if os.getenv('TAR_SCM_CLEAN_ENV'):
            logging.info("Ignoring config files: test-mode detected")

        # fake a section header for configuration files
        for tmp in files:
            fname = tmp[0]
            self.fakeheader = tmp[1]
            if not os.path.isfile(fname):
                logging.debug("Config file not found: %s", fname)
                continue
            self.configs.append(self._init_config(fname))

        # strip quotes from pathname
        for config in self.configs:
            for section in config.sections():
                for opt in config.options(section):
                    config.set(
                        section,
                        opt,
                        re.sub(
                            r'"(.*)"',
                            r'\1',
                            config.get(section, opt)
                        )
                    )

    def _init_config(self, fname: str) -> Any:
        config = configparser.RawConfigParser()
        config.optionxform = str  # type: ignore

        if self.fakeheader:
            logging.debug("Using fakeheader for file '%s'", fname)
            fake_header = '[' + self.default_section + ']\n'
            with open(fname, 'r', encoding='utf-8') as config_file:
                tmp_fp = StringIO(fake_header + config_file.read())
            config.read_file(tmp_fp, source=fname)

        else:
            config.read(fname)

        return config

    def get(self, section: Optional[str], option: str) -> Optional[str]:
        value = None
        # We're in test-mode, so don't let any local site-wide
        # or per-user config impact the test suite.
        if os.getenv('TAR_SCM_CLEAN_ENV'):
            return value

        if section is None and self.fakeheader:
            section = self.default_section

        logging.debug("SECTION: %s", section)
        for config in self.configs:
            try:
                value = config.get(section, option)
            except:
                pass

        return value
