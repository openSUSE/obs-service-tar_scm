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

sys.path.append(os.path.dirname(os.path.abspath(__file__)))  # noqa

# These two modules have to be imported after sys.path.append because
# the additional path is where the modules are found
import TarSCM        # pylint: disable=wrong-import-position
import TarSCM.tasks  # pylint: disable=wrong-import-position


def main():
    TarSCM.run()

if __name__ == '__main__':
    main()
