from __future__ import print_function

import argparse
import os
import sys
import locale
import subprocess
import logging


def contains_dotdot(files):
    if files:
        for index, fname in enumerate(files):
            fname = os.path.normpath(fname)
            for part in fname.split('/'):
                if part == '..':
                    return 1
            files[index] = fname
    return 0


def check_locale(loc):
    try:
        aloc_tmp = subprocess.check_output(['locale', '-a'])
    except AttributeError:
        aloc_tmp, _ = subprocess.Popen(['locale', '-a'],
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT).communicate()
    aloc = {}

    for tloc in aloc_tmp.split(b'\n'):
        aloc[tloc] = 1

    for tloc in loc:
        logging.debug("Checking .... %s", tloc)
        try:
            if aloc[tloc.encode()]:
                return tloc
        except KeyError:
            pass

    return 'C'


class Cli():
    # pylint: disable=too-few-public-methods
    # pylint: disable=too-many-instance-attributes
    DEFAULT_AUTHOR = 'service_run'
    DEFAULT_EMAIL = 'obs-service-tar-scm@invalid'
    outdir = None

    def __init__(self):
        self.use_obs_scm = False
        self.snapcraft   = False
        self.appimage    = False
        self.maintainers_asc = None
        self.url = None
        self.revision = None
        self.user = None
        self.keyring_passphrase = None
        self.changesgenerate = False

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
        parser.add_argument('--user',
                            help='Specify user for SCM authentication')
        parser.add_argument('--keyring-passphrase',
                            help='Specify passphrase to decrypt credentials '
                                 'from keyring')
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
                                 'written. Defaults to VC_REALNAME env '
                                 'variable, set by osc. Or "%s", otherwise.' %
                            self.DEFAULT_AUTHOR)
        parser.add_argument('--changesemail',
                            help='The author\'s email of the changes file '
                                 'entry to be written. Defaults to VC_MAILADDR'
                                 ' env variable, set by osc. Or "%s", '
                                 'otherwise.' %
                            self.DEFAULT_EMAIL)
        parser.add_argument('--subdir', default='',
                            help='Package just a subdirectory of the sources')
        parser.add_argument('--submodules',
                            choices=['enable', 'master', 'main', 'disable'],
                            default='enable',
                            help='Whether or not to include git submodules '
                                 'from SCM commit log since a given parent '
                                 'revision (see changesrevision). Use '
                                 '\'master\' or \'main\' to fetch the latest'
                                 'development revision.')
        parser.add_argument('--lfs',
                            choices=['enable', 'disable'],
                            default='disable',
                            help='Whether or not to include git lfs blobs '
                                 'from SCM commit log since a given parent '
                                 'revision (see changesrevision).')
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
                                 '(Only for debugging)')
        parser.add_argument('--locale',
                            help='DEPRECATED - Please use "encoding" instead.'
                                 ' Set locale while service run')
        parser.add_argument('--encoding',
                            help='set encoding while service run')
        parser.add_argument('--use-obs-gbp', default = False,
                            help='use obs gbp (requires git-buildpackage) ')
        parser.add_argument('--latest-signed-commit', default = False,
                            help='use the latest signed commit on a branch ')
        parser.add_argument('--latest-signed-tag', default = False,
                            help='use the latest signed tag on a branch ')
        parser.add_argument('--maintainers-asc', default = False,
                            help='File which contains maintainers pubkeys. '
                                 '(only used with \'--latest-signed-*\')')
        parser.add_argument('--without-version', default = False,
                            help='Do not add version to output file.')

        self.verify_args(parser.parse_args(options))

    def verify_args(self, args):
        # basic argument validation
        # pylint: disable=too-many-branches
        if not os.path.isdir(args.outdir):
            sys.exit("%s: No such directory" % args.outdir)

        args.outdir = os.path.abspath(args.outdir)
        orig_subdir = args.subdir
        if orig_subdir:
            args.subdir = os.path.normpath(orig_subdir)
        if args.subdir.startswith('/'):
            sys.exit("Absolute path '%s' is not allowed for --subdir" %
                     orig_subdir)

        if contains_dotdot([args.subdir]):
            sys.exit("--subdir path '%s' must stay within repo" % orig_subdir)

        if args.history_depth:
            print("history-depth parameter is obsolete and will be ignored")

        if contains_dotdot(args.extract):
            sys.exit('--extract is not allowed to contain ".."')

        if args.filename and "/" in args.filename:
            sys.exit('--filename must not specify a path')

        # booleanize non-standard parameters
        args.changesgenerate      = bool(args.changesgenerate == 'enable')
        args.package_meta         = bool(args.package_meta == 'yes')
        args.sslverify            = bool(args.sslverify != 'disable')
        args.use_obs_scm          = bool(args.use_obs_scm)
        args.use_obs_gbp          = bool(args.use_obs_gbp)
        args.latest_signed_commit = bool(args.latest_signed_commit)
        args.latest_signed_tag    = bool(args.latest_signed_tag)
        t_gbp_dch_release_u = bool(args.gbp_dch_release_update != 'disable')
        args.gbp_dch_release_update = t_gbp_dch_release_u

        if args.latest_signed_commit and args.latest_signed_tag:
            sys.exit('--latest-signed-commit '
                     'and --latest-signed-tag specified. '
                     'Please choose only one!')

        latest_signed = args.latest_signed_commit or args.latest_signed_tag

        if args.maintainers_asc and not latest_signed:
            sys.exit('Specifying "--maintainers-asc" without'
                     ' --latest-signed-commit or --latest-signed-tag'
                     ' makes no sense. Please adjust your settings!')

        # Allow forcing verbose mode from the environment; this
        # allows debugging when running "osc service disabledrun" etc.
        if bool(os.getenv('DEBUG_TAR_SCM')) or args.verbose:
            logging.basicConfig(format='%(asctime)s %(message)s')
            logging.getLogger().setLevel(logging.DEBUG)

        for attr in args.__dict__.keys():
            self.__dict__[attr] = args.__dict__[attr]

        if args.locale:
            use_locale = args.locale
        elif args.encoding:
            use_locale = check_locale([
                "en_US.%s" % args.encoding,
                "C.%s" % args.encoding])
        else:
            use_locale = check_locale(["en_US.utf8", 'C.utf8'])

        logging.debug("Using locale: %s", use_locale)

        locale.setlocale(locale.LC_ALL, use_locale)

        os.environ["LC_ALL"] = use_locale
        os.environ["LANG"] = use_locale
        os.environ["LANGUAGE"] = use_locale

        return args
