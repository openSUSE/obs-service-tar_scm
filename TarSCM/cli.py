import argparse
import os
import sys


class cli():
    DEFAULT_AUTHOR = 'opensuse-packaging@opensuse.org'

    def __init__(self):
        self.use_obs_scm = False
        self.snapcraft   = False

    def parse_args(self, options):
        parser = argparse.ArgumentParser(description='Git Tarballs')
        parser.add_argument('-v', '--verbose', action='store_true',
                            default=False,
                            help='Enable verbose output')
        parser.add_argument('--scm',
                            help='Specify SCM',
                            choices=['git', 'hg', 'bzr', 'svn', 'tar'])
        parser.add_argument('--url',
                            help='Specify URL of upstream tarball to download')
        parser.add_argument('--obsinfo',
                            help='Specify .obsinfo file to create a tar ball')
        parser.add_argument('--version', default='_auto_',
                            help='Specify version to be used in tarball. '
                                 'Defaults to automatically detected value '
                                 'formatted by versionformat parameter.')
        parser.add_argument('--versionformat',
                            help='Auto-generate version from checked out '
                                 'source using this format string. '
                                 'This parameter is used if the \'version\' '
                                 'parameter is not specified.')
        parser.add_argument('--versionprefix',
                            help='Specify a base version as prefix.')
        parser.add_argument('--parent-tag',
                            help='Override base commit for @TAG_OFFSET@')
        parser.add_argument('--revision',
                            help='Specify revision to package')
        parser.add_argument('--extract', action='append',
                            help='Extract a file directly. Useful for build'
                                 'descriptions')
        parser.add_argument('--filename',
                            help='Name of package - used together with version'
                                 ' to determine tarball name')
        parser.add_argument('--extension', default='tar',
                            help='suffix name of package - used together with '
                                 'filename to determine tarball name')
        parser.add_argument('--changesgenerate', choices=['enable', 'disable'],
                            default='disable',
                            help='Specify whether to generate changes file '
                                 'entries from SCM commit log since a given '
                                 'parent revision (see changesrevision).')
        parser.add_argument('--changesauthor',
                            help='The author of the changes file entry to be '
                                 'written, defaults to first email entry in '
                                 '~/.oscrc or "%s" '
                                 'if there is no ~/.oscrc found.' %
                                 self.DEFAULT_AUTHOR)
        parser.add_argument('--subdir', default='',
                            help='Package just a subdirectory of the sources')
        parser.add_argument('--submodules',
                            choices=['enable', 'master', 'disable'],
                            default='enable',
                            help='Whether or not to include git submodules '
                                 'from SCM commit log since a given parent '
                                 'revision (see changesrevision). Use '
                                 '\'master\' to fetch the latest master.')
        parser.add_argument('--sslverify', choices=['enable', 'disable'],
                            default='enable',
                            help='Whether or not to check server certificate '
                                 'against installed CAs.')
        group = parser.add_mutually_exclusive_group()
        group.add_argument('--include', action='append',
                           default=[], metavar='REGEXP',
                           help='Specifies subset of files/subdirectories to '
                                'pack in the tarball (can be repeated)')
        group.add_argument('--exclude', action='append',
                           default=[], metavar='REGEXP',
                           help='Specifies excludes when creating the '
                                'tarball (can be repeated)')
        parser.add_argument('--package-meta',
                            choices=['yes', 'no'], default='no',
                            help='Package the meta data of SCM to allow the '
                                 'user or OBS to update after un-tar')
        parser.add_argument('--outdir', required=True,
                            help='osc service parameter for internal use only '
                                 '(determines where generated files go before '
                                 'collection')
        parser.add_argument('--jailed', required=False, type=int, default=0,
                            help='service parameter for internal use only '
                                 '(determines whether service runs in docker '
                                 'jail)')
        parser.add_argument('--history-depth',
                            help='Obsolete osc service parameter that does '
                                 'nothing')
        args = parser.parse_args(options)

        # basic argument validation
        if not os.path.isdir(args.outdir):
            sys.exit("%s: No such directory" % args.outdir)

        args.outdir = os.path.abspath(args.outdir)
        orig_subdir = args.subdir
        args.subdir = os.path.normpath(orig_subdir)
        if args.subdir.startswith('/'):
            sys.exit("Absolute path '%s' is not allowed for --subdir" %
                     orig_subdir)
        if args.subdir == '..' or args.subdir.startswith('../'):
            sys.exit("--subdir path '%s' must stay within repo" % orig_subdir)

        if args.history_depth:
            print("history-depth parameter is obsolete and will be ignored")

        # booleanize non-standard parameters
        if args.changesgenerate == 'enable':
            args.changesgenerate = True
        else:
            args.changesgenerate = False

        if args.package_meta == 'yes':
            args.package_meta = True
        else:
            args.package_meta = False

        args.sslverify = False if args.sslverify == 'disable' else True

        # force verbose mode in test-mode
        if os.getenv('DEBUG_TAR_SCM'):
            args.verbose = True

        for attr in args.__dict__.keys():
            self.__dict__[attr] = args.__dict__[attr]

        return args
