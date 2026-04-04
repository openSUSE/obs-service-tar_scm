from __future__ import print_function

import datetime
import os
import logging
import subprocess
import io
from typing import Any, List, Optional, Tuple


def file_write_legacy(fname: str, string: Any, *args: str) -> None:
    '''function to write string to file python 2/3 compatible'''
    mode = 'w'
    if args:
        mode = args[0]

    with io.open(fname, mode, encoding='utf-8') as outfile:
        # 'str().encode().decode()' is required for pyhton 2/3 compatibility
        outfile.write(str(string).encode('UTF-8').decode('UTF-8'))


class Helpers():
    def run_cmd(self, cmd: List[str], cwd: Optional[str], interactive: bool=False, raisesysexit: bool=False) -> Tuple[int, str]:
        """
        Execute the command cmd in the working directory cwd and check return
        value. If the command returns non-zero and raisesysexit is True raise a
        SystemExit exception otherwise return a tuple of return code and
        command output.
        """
        logging.debug("COMMAND: %s" % cmd)

        proc = subprocess.Popen(cmd,
                                shell=False,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                cwd=cwd)
        output = ''
        if interactive:
            stdout_lines = []
            stdout = proc.stdout
            while proc.poll() is None:
                if stdout is None:
                    break
                for line in stdout:
                    line_str = line.rstrip().decode('UTF-8')
                    print(line_str)
                    stdout_lines.append(line_str)
            output = '\n'.join(stdout_lines)
            output = output
        else:
            raw_output = proc.communicate()[0]
            if isinstance(raw_output, bytes):
                output = raw_output.decode('UTF-8')
            else:
                output = raw_output

        if proc.returncode and raisesysexit:
            logging.info("ERROR(%d): %s", proc.returncode, repr(output))
            raise SystemExit(
                "Command %s failed(%d): '%s'" % (cmd, proc.returncode, output)
            )
        else:
            logging.debug("RESULT(%d): %s", proc.returncode, repr(output))

        return (proc.returncode, output)

    def safe_run(self, cmd: List[str], cwd: Optional[str], interactive: bool=False) -> Tuple[int, str]:
        """Execute the command cmd in the working directory cwd and check
        return value. If the command returns non-zero raise a SystemExit
        exception.
        """
        result = self.run_cmd(cmd, cwd, interactive, raisesysexit=True)
        return result

    def get_timestamp(self, scm_object: Any, args: Any, clone_dir: str) -> int:
        """Returns the commit timestamp for checked-out repository."""

        timestamp = scm_object.get_timestamp()
        logging.debug("COMMIT TIMESTAMP: %s (%s)", timestamp,
                      datetime.datetime.fromtimestamp(timestamp).strftime(
                          '%Y-%m-%d %H:%M:%S'))
        return timestamp
