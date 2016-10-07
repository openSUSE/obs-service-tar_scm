#!/usr/bin/env python
#
# A simple script to checkout or update a svn or git repo as source service
#
# (C) 2010 by Adrian Schroeter <adrian@suse.de>
# (C) 2014 by Jan Blunck <jblunck@infradead.org> (Python rewrite)
# (C) 2016 by Adrian Schroeter <adrian@suse.de> (OBS cpio support)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
# See http://www.gnu.org/licenses/gpl-2.0.html for full license text.
import os
import sys



sys.path.append(os.path.dirname(os.path.abspath(__file__)))


import TarSCM
import TarSCM.tasks
from TarSCM.exceptions import OptionsError

def main():
    cli = TarSCM.cli()
    cli.parse_args(sys.argv[1:])

    if os.path.basename(sys.argv[0]) == "tar":
        cli.scm = "tar"
    
    if os.path.basename(sys.argv[0]) == "obs_scm":
        cli.use_obs_scm = True

    if  os.path.basename(sys.argv[0]) == "snapcraft":
        cli.snapcraft = True

    task_list = TarSCM.tasks()

    task_list.generate_list(cli)

    try:
        task_list.process_list()
    except OptionsError as e:
        print(e)
        sys.exit(1)

    task_list.finalize(cli)


if __name__ == '__main__':
    main()
