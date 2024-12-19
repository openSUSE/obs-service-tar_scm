from __future__ import print_function

import datetime
import os
import logging
import subprocess
import io

# python3 renaming of StringIO
try:
    import StringIO
except:
    from io import StringIO


def file_write_legacy(fname, string, *args):
    '''function to write string to file python 2/3 compatible'''
    mode = 'w'
    if args:
        mode = args[0]

    with io.open(fname, mode, encoding='utf-8') as outfile:
        # 'str().encode().decode()' is required for pyhton 2/3 compatibility
        outfile.write(str(string).encode('UTF-8').decode('UTF-8'))


class Helpers():
    def run_cmd(self, cmd, cwd, interactive=False, raisesysexit=False, env={}):
        """
        Execute the command cmd in the working directory cwd and check return
        value. If the command returns non-zero and raisesysexit is True raise a
        SystemExit exception otherwise return a tuple of return code and
        command output.
        """
        logging.debug("COMMAND: %s" % cmd)

        if env:
            env.update(dict(os.environ))

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
                    line_str = line.rstrip().decode('UTF-8')
                    print(line_str)
                    stdout_lines.append(line_str)
            output = '\n'.join(stdout_lines)
            output = output
        else:
            output = proc.communicate()[0]
            if isinstance(output, bytes):
                output = output.decode('UTF-8')

        if proc.returncode and raisesysexit:
            logging.info("ERROR(%d): %s", proc.returncode, repr(output))
            raise SystemExit(
                "Command %s failed(%d): '%s'" % (cmd, proc.returncode, output)
            )
        else:
            logging.debug("RESULT(%d): %s", proc.returncode, repr(output))

        return (proc.returncode, output)

    def safe_run(self, cmd, cwd, interactive=False, env={}):
        """Execute the command cmd in the working directory cwd and check
        return value. If the command returns non-zero raise a SystemExit
        exception.
        """
        result = self.run_cmd(cmd, cwd, interactive, raisesysexit=True, env=env)
        return result

    def get_timestamp(self, scm_object, args, clone_dir):
        """Returns the commit timestamp for checked-out repository."""

        timestamp = scm_object.get_timestamp()
        logging.debug("COMMIT TIMESTAMP: %s (%s)", timestamp,
                      datetime.datetime.fromtimestamp(timestamp).strftime(
                          '%Y-%m-%d %H:%M:%S'))
        return timestamp
