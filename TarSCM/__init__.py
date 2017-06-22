from __future__ import print_function

import sys
import os

from TarSCM.tasks      import tasks
from TarSCM.helpers    import helpers
from TarSCM.cli        import Cli
from TarSCM.archive    import Tar
from TarSCM.archive    import ObsCpio
from TarSCM.exceptions import OptionsError


def run():
    _cli = Cli()
    _cli.parse_args(sys.argv[1:])

    if os.path.basename(sys.argv[0]) == "tar":
        _cli.scm = "tar"

    if os.path.basename(sys.argv[0]) == "obs_scm":
        _cli.use_obs_scm = True

    if os.path.basename(sys.argv[0]) == "appimage":
        _cli.appimage = True

    if os.path.basename(sys.argv[0]) == "snapcraft":
        _cli.snapcraft = True

    task_list = tasks()

    task_list.generate_list(_cli)

    try:
        task_list.process_list()
    except OptionsError as exc:
        print(exc)
        sys.exit(1)

    task_list.finalize(_cli)

    task_list.cleanup()

    raise SystemExit(0)
