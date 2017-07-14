from __future__ import print_function

import argparse
import os
import sys


class Cli():
    # pylint: disable=too-few-public-methods
    DEFAULT_AUTHOR = 'opensuse-packaging@opensuse.org'

    def __init__(self):
        self.use_obs_scm = False
        self.snapcraft   = False
        self.appimage    = False

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
        parser.add_argument('--versionrewrite-pattern',
                            help='Regex used to rewrite the version which is '
                                 'applied post versionformat. For example, to '
                                 'remove a tag prefix of "v" the regex '
                                 '"v(.*)" could be used. See the '
                                 'versionrewrite-replacement parameter.')
        parser.add_argument('--versionrewrite-replacement',
                            default=r'\1',
                            help='Replacement applied to rewrite pattern. '
                                 'Typically backreferences are useful and as '
                                 'such defaults to \\1.')
        parser.add_argument('--versionprefix',
                            help='Specify a base version as prefix.')
        parser.add_argument('--parent-tag',
                            help='Override base commit for @TAG_OFFSET@')
        parser.add_argument('--match-tag',
                            help='tag must match glob(7)')
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
        parser.add_argument('--history-depth',
                            help='Obsolete osc service parameter that does '
                                 'nothing')
        parser.add_argument('--gbp-build-args', type=str,
                            default='-nc -uc -us -S',
                            help='Parameters passed to git-buildpackage')
        parser.add_argument('--gbp-dch-release-update',
                            choices=['enable', 'disable'], default='disable',
                            help='Append OBS release number')
        # These option is only used in test cases, in real life you would call
        # obs_scm or obs_gbp instead
        parser.add_argument('--use-obs-scm', default = False,
                            help='use obs scm (obscpio) ')

        parser.add_argument('--skip-cleanup', default = False,
                            action='store_true',
                            help='do not cleanup directories before exiting '
                                 '(Only for debugging')
        parser.add_argument('--use-obs-gbp', default = False,
                            help='use obs gbp (requires git-buildpackage) ')
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
        args.changesgenerate = bool(args.changesgenerate == 'enable')
        args.package_meta    = bool(args.package_meta == 'yes')
        args.sslverify       = bool(args.sslverify != 'disable')
        args.use_obs_scm     = bool(args.use_obs_scm)
        args.use_obs_gbp     = bool(args.use_obs_gbp)
        args.gbp_dch_release_update = bool(args.gbp_dch_release_update !=
                                           'disable')
        # git-buildpackage, as the name suggets, supports only git
        if args.use_obs_gbp:
            args.scm = 'git'

        # force verbose mode in test-mode
        args.verbose = bool(os.getenv('DEBUG_TAR_SCM'))

        for attr in args.__dict__.keys():
            self.__dict__[attr] = args.__dict__[attr]

        return args
