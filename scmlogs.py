#!/usr/bin/python

import glob
import os

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
    def setup_bin_wrapper(cls, scm, tmp_dir):
        cls.wrapper_dir = tmp_dir + '/wrappers'

        if not os.path.exists(cls.wrapper_dir):
            os.makedirs(cls.wrapper_dir)

        wrapper = cls.wrapper_dir + '/' + scm
        if not os.path.exists(wrapper):
            os.symlink('../../scm-wrapper', wrapper)

        path = os.getenv('PATH')
        prepend = cls.wrapper_dir + ':'

        if not path.startswith(prepend):
            new_path = prepend + path
            os.environ['PATH'] = new_path

    def __init__(self, scm, test_dir):
        self.scm = scm
        self.test_dir = test_dir
        self.counter = 0
        self.unlink_existing_logs()

    def get_log_file_template(self):
        return '%s-invocation-%%s.log' % self.scm

    def get_log_path_template(self):
        return os.path.join(self.test_dir, self.get_log_file_template())

    def unlink_existing_logs(self):
        pat = self.get_log_path_template() % '*'
        for log in glob.glob(pat):
            os.unlink(log)

    def get_log_file(self, identifier):
        if identifier:
            identifier = '-' + identifier
        return self.get_log_file_template() % ('%02d%s' % (self.counter, identifier))

    def get_log_path(self, identifier):
        return os.path.join(self.test_dir, self.get_log_file(identifier))

    def next(self, identifier=''):
        self.counter += 1
        self.current_log_path = self.get_log_path(identifier)
        if os.path.exists(self.current_log_path):
            raise RuntimeError, "%s already existed?!" % self.current_log_path
        os.putenv('SCM_INVOCATION_LOG', self.current_log_path)

    def annotate(self, msg):
        log = open(self.current_log_path, 'a')
        log.write('# ' + msg + "\n")
        print msg
        log.close()

    def read(self):
        if not os.path.exists(self.current_log_path):
            return '<no %s log>' % self.scm

        log = open(self.current_log_path)
        loglines = log.readlines()
        log.close()
        return loglines
