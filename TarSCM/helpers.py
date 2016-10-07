import datetime
import ConfigParser
import os
import StringIO
import logging
import subprocess

class helpers():
    def run_cmd(self, cmd, cwd, interactive=False, raisesysexit=False):
        """Execute the command cmd in the working directory cwd and check return
        value. If the command returns non-zero and raisesysexit is True raise a
        SystemExit exception otherwise return a tuple of return code and command
        output.
        """
        logging.debug("COMMAND: %s", cmd)

        # Ensure we get predictable results when parsing the output of commands
        # like 'git branch'
        env = os.environ.copy()
        env['LANG'] = 'C'

        proc = subprocess.Popen(cmd,
                                shell=False,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                cwd=cwd,
                                env=env)
        output = ''
        if interactive:
            stdout_lines = []
            while proc.poll() is None:
                for line in proc.stdout:
                    print line.rstrip()
                    stdout_lines.append(line.rstrip())
            output = '\n'.join(stdout_lines)
        else:
            output = proc.communicate()[0]

        if proc.returncode and raisesysexit:
            logging.info("ERROR(%d): %s", proc.returncode, repr(output))
            sys.exit("Command failed(%d): %s" % (proc.returncode, repr(output)))
        else:
            logging.debug("RESULT(%d): %s", proc.returncode, repr(output))
        return (proc.returncode, output)

    def safe_run(self, cmd, cwd, interactive=False):
        """Execute the command cmd in the working directory cwd and check return
        value. If the command returns non-zero raise a SystemExit exception.
        """
        return self.run_cmd(cmd, cwd, interactive, raisesysexit=True)

    def get_config_options(self):
	"""Read user-specific and system-wide service configuration files, if not
	in test-mode. This function returns an instance of ConfigParser.
	"""
	config = ConfigParser.RawConfigParser()
	config.optionxform = str

	# We're in test-mode, so don't let any local site-wide
	# or per-user config impact the test suite.
	if os.getenv('DEBUG_TAR_SCM'):
	    logging.info("Ignoring config files: test-mode detected")
	    return config

	# fake a section header for configuration files
	for fname in ['/etc/obs/services/tar_scm',
		      os.path.expanduser('~/.obs/tar_scm')]:
	    try:
		tmp_fp = StringIO.StringIO()
		tmp_fp.write('[tar_scm]\n')
		tmp_fp.write(open(fname, 'r').read())
		tmp_fp.seek(0, os.SEEK_SET)
		config.readfp(tmp_fp)
	    except (OSError, IOError):
		continue

	# strip quotes from pathname
	if config.has_section('tar_scm'):
	    for opt in config.options('tar_scm'):
		config.set('tar_scm', opt, re.sub(r'"(.*)"', r'\1',
						  config.get('tar_scm', opt)))

	return config

    def get_timestamp(self, scm_object, args, clone_dir):
        """Returns the commit timestamp for checked-out repository."""

        timestamp = scm_object.get_timestamp(args, clone_dir)
        logging.debug("COMMIT TIMESTAMP: %s (%s)", timestamp,
                      datetime.datetime.fromtimestamp(timestamp).strftime(
                          '%Y-%m-%d %H:%M:%S'))
        return timestamp
