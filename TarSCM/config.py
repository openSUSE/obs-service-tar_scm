import os
import logging
import re

# python3 renaming of StringIO
try:
    from StringIO import StringIO
except:
    from io import StringIO

# python3 renaming of ConfigParser
try:
    import configparser
except:
    import ConfigParser as configparser


class Config():
    # pylint: disable=too-few-public-methods
    def __init__(
            self,
            files=[['/etc/obs/services/tar_scm', True]]
    ):
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
        if os.getenv('DEBUG_TAR_SCM'):
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

    def _init_config(self, fname):
        config = configparser.RawConfigParser()
        config.optionxform = str

        if self.fakeheader:
            logging.debug("Using fakeheader for file '%s'", fname)
            tmp_fp = StringIO()
            tmp_fp.write('[' + self.default_section + ']\n')
            tmp_fp.write(open(fname, 'r').read())
            tmp_fp.seek(0, os.SEEK_SET)
            config.readfp(tmp_fp)
        else:
            config.read(fname)

        return config

    def get(self, section, option):
        value = None
        # We're in test-mode, so don't let any local site-wide
        # or per-user config impact the test suite.
        if os.getenv('DEBUG_TAR_SCM'):
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
