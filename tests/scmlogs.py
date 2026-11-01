#!/usr/bin/env python
from typing import List, Optional
import glob
import os
import tempfile
import io

from tests.utils import file_write_legacy


class ScmInvocationLogs:
    """
    Provides log files which tracks invocations of SCM binaries.  The
    tracking is done via a wrapper around SCM to enable behaviour
    verification testing on tar_scm's repository caching code.  This
    is cleaner than writing tests which look inside the cache, because
    then they become coupled to the cache's implementation, and
    require knowledge of where the cache lives etc.

    One instance should be constructed per unit test.  If the test
    invokes the SCM binary multiple times, invoke next() in between
    each, so that a separate log file is used for each invocation -
    this allows more accurate fine-grained assertions on the
    invocation log.
    """

    @classmethod
    def setup_bin_wrapper(cls, scm: str, tests_dir: str) -> None:
        wrapper_dir = tempfile.mkdtemp(dir="/tmp")

        wrapper_src = os.path.join(tests_dir, 'scm-wrapper')
        wrapper_dst = wrapper_dir + '/' + scm

        if not os.path.exists(wrapper_dst):
            os.symlink(wrapper_src, wrapper_dst)

        path = os.getenv('PATH') or ''
        prepend = wrapper_dir + ':'

        if not path.startswith(prepend):
            new_path = prepend + path
            os.environ['PATH'] = new_path

    def __init__(self, scm: str, test_dir: str) -> None:
        self.scm              = scm
        self.test_dir         = test_dir
        self.counter          = 0
        self.current_log_path = None  # type: Optional[str]

        self.unlink_existing_logs()

    def get_log_file_template(self) -> str:
        return '%s-invocation-%%s.log' % self.scm

    def get_log_path_template(self) -> str:
        return os.path.join(self.test_dir, self.get_log_file_template())

    def unlink_existing_logs(self) -> None:
        pat = self.get_log_path_template() % '*'
        for log in glob.glob(pat):
            os.unlink(log)

    def get_log_file(self, identifier: str) -> str:
        if identifier:
            identifier = '-' + identifier
        return self.get_log_file_template() % \
            ('%02d%s' % (self.counter, identifier))

    def get_log_path(self, identifier: str) -> str:
        return os.path.join(self.test_dir, self.get_log_file(identifier))

    def nextlog(self, identifier: str='') -> None:
        self.counter += 1
        current_log_path = self.get_log_path(identifier)
        self.current_log_path = current_log_path
        if os.path.exists(current_log_path):
            raise RuntimeError("%s already existed?!" % current_log_path)
        os.putenv('SCM_INVOCATION_LOG', current_log_path)
        os.environ['SCM_INVOCATION_LOG'] = current_log_path

    def annotate(self, msg: str) -> None:
        print(msg)
        if self.current_log_path is None:
            raise RuntimeError('No current log path set')
        file_write_legacy(self.current_log_path, '# ' + msg + "\n", 'a')

    def read(self) -> List[str]:
        if self.current_log_path is None:
            raise RuntimeError('No current log path set')
        if not os.path.exists(self.current_log_path):
            return ['<no %s log>' % self.scm]
        with io.open(self.current_log_path, 'r', encoding="UTF-8") as log:
            loglines = log.readlines()
        return loglines
