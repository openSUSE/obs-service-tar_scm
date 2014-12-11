#!/usr/bin/env python2
#
# A simple script to checkout or update a svn or git repo as source service
#
# (C) 2010 by Adrian Schroeter <adrian@suse.de>
# (C) 2014 by Jan Blunck <jblunck@infradead.org> (Python rewrite)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
# See http://www.gnu.org/licenses/gpl-2.0.html for full license text.

import argparse
import atexit
import ConfigParser
import datetime
import fnmatch
import glob
import hashlib
import logging
import os
import re
import shutil
import StringIO
import subprocess
import sys
import tarfile
import tempfile
from urlparse import urlparse

DEFAULT_AUTHOR = 'opensuse-packaging@opensuse.org'


def safe_run(cmd, cwd, interactive=False):
    """Execute the command cmd in the working directory cwd and check return
    value. If the command returns non-zero raise a SystemExit exception.
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

    if proc.returncode:
        logging.info("ERROR(%d): %s", proc.returncode, repr(output))
        sys.exit("Command failed(%d): %s" % (proc.returncode, repr(output)))
    else:
        logging.debug("RESULT(%d): %s", proc.returncode, repr(output))
    return (proc.returncode, output)


def fetch_upstream_git(url, clone_dir, revision, cwd, kwargs):
    """Fetch sources via git."""
    safe_run(['git', 'clone', url, clone_dir], cwd=cwd,
             interactive=sys.stdout.isatty())
    if 'submodules' in kwargs and kwargs['submodules']:
        safe_run(['git', 'submodule', 'update', '--init', '--recursive'],
                 clone_dir)


def fetch_upstream_svn(url, clone_dir, revision, cwd, kwargs):
    """Fetch sources via svn."""
    command = ['svn', 'checkout', '--non-interactive', url, clone_dir]
    if revision:
        command.insert(4, '-r%s' % revision)
    safe_run(command, cwd, interactive=sys.stdout.isatty())


def fetch_upstream_hg(url, clone_dir, revision, cwd, kwargs):
    """Fetch sources via hg."""
    safe_run(['hg', 'clone', url, clone_dir], cwd,
             interactive=sys.stdout.isatty())


def fetch_upstream_bzr(url, clone_dir, revision, cwd, kwargs):
    """Fetch sources from bzr."""
    command = ['bzr', 'checkout', url, clone_dir]
    if revision:
        command.insert(3, '-r')
        command.insert(4, revision)
    safe_run(command, cwd, interactive=sys.stdout.isatty())


FETCH_UPSTREAM_COMMANDS = {
    'git': fetch_upstream_git,
    'svn': fetch_upstream_svn,
    'hg':  fetch_upstream_hg,
    'bzr': fetch_upstream_bzr,
}


def update_cache_git(url, clone_dir, revision):
    """Update sources via git."""
    safe_run(['git', 'fetch', '--tags'],
             cwd=clone_dir, interactive=sys.stdout.isatty())
    safe_run(['git', 'fetch'],
             cwd=clone_dir, interactive=sys.stdout.isatty())


def update_cache_svn(url, clone_dir, revision):
    """Update sources via svn."""
    command = ['svn', 'update']
    if revision:
        command.insert(3, "-r%s" % revision)
    safe_run(command, cwd=clone_dir, interactive=sys.stdout.isatty())


def update_cache_hg(url, clone_dir, revision):
    """Update sources via hg."""
    try:
        safe_run(['hg', 'pull'], cwd=clone_dir,
                 interactive=sys.stdout.isatty())
    except SystemExit, e:
        # Contrary to the docs, hg pull returns exit code 1 when
        # there are no changes to pull, but we don't want to treat
        # this as an error.
        if re.match('.*no changes found.*', e.message) is None:
            raise


def update_cache_bzr(url, clone_dir, revision):
    """Update sources via bzr."""
    command = ['bzr', 'update']
    if revision:
        command.insert(3, '-r')
        command.insert(4, revision)
    safe_run(command, cwd=clone_dir, interactive=sys.stdout.isatty())


UPDATE_CACHE_COMMANDS = {
    'git': update_cache_git,
    'svn': update_cache_svn,
    'hg':  update_cache_hg,
    'bzr': update_cache_bzr,
}


def switch_revision_git(clone_dir, revision):
    """Switch sources to revision. The git revision may refer to any of the
    following:

    - explicit SHA1: a1b2c3d4....
    - the SHA1 must be reachable from a default clone/fetch (generally, must be
      reachable from some branch or tag on the remote).
    - short branch name: "master", "devel" etc.
    - explicit ref: refs/heads/master, refs/tags/v1.2.3,
      refs/changes/49/11249/1
    """
    if revision is None:
        revision = 'master'

    revs = [x + revision for x in ['origin/', '']]
    for rev in revs:
        try:
            safe_run(['git', 'rev-parse', '--verify', '--quiet', rev],
                     cwd=clone_dir)
            text = safe_run(['git', 'reset', '--hard', rev], cwd=clone_dir)[1]
            print text.rstrip()
            break
        except SystemExit:
            continue
    else:
        sys.exit('%s: No such revision' % revision)

    # only update submodules if they have been enabled
    if os.path.exists(
            os.path.join(clone_dir, os.path.join('.git', 'modules'))):
        safe_run(['git', 'submodule', 'update', '--recursive'], cwd=clone_dir)


def switch_revision_hg(clone_dir, revision):
    """Switch sources to revision."""
    if revision is None:
        revision = 'tip'

    try:
        safe_run(['hg', 'update', revision], cwd=clone_dir,
                 interactive=sys.stdout.isatty())
    except SystemExit:
        sys.exit('%s: No such revision' % revision)


def switch_revision_none(clone_dir, revision):
    """Switch sources to revision. Dummy implementation for version control
    systems that change revision during fetch/update.
    """
    return


SWITCH_REVISION_COMMANDS = {
    'git': switch_revision_git,
    'svn': switch_revision_none,
    'hg':  switch_revision_hg,
    'bzr': switch_revision_none,
}


def _calc_dir_to_clone_to(scm, url, out_dir):
    # separate path from parameters etc.
    url_path = urlparse(url)[2].rstrip('/')

    # remove trailing scm extension
    url_path = re.sub(r'\.%s$' % scm, '', url_path)

    # special handling for cloning bare repositories (../repo/.git/)
    url_path = url_path.rstrip('/')

    basename = os.path.basename(os.path.normpath(url_path))
    clone_dir = os.path.abspath(os.path.join(out_dir, basename))
    return clone_dir


def fetch_upstream(scm, url, revision, out_dir, **kwargs):
    """Fetch sources from repository and checkout given revision."""
    clone_dir = _calc_dir_to_clone_to(scm, url, out_dir)

    if not os.path.isdir(clone_dir):
        # initial clone
        os.mkdir(clone_dir)
        if scm not in FETCH_UPSTREAM_COMMANDS:
            sys.exit("Don't know how to fetch for '%s' SCM" % scm)
        FETCH_UPSTREAM_COMMANDS[scm](url, clone_dir, revision, cwd=out_dir,
                                     kwargs=kwargs)
    else:
        logging.info("Detected cached repository...")
        UPDATE_CACHE_COMMANDS[scm](url, clone_dir, revision)

    # switch_to_revision
    SWITCH_REVISION_COMMANDS[scm](clone_dir, revision)

    return clone_dir


def prep_tree_for_tar(repodir, subdir, outdir, dstname):
    """Prepare directory tree for creation of the tarball by copying the
    requested sub-directory to the top-level destination directory.
    """
    src = os.path.join(repodir, subdir)
    if not os.path.exists(src):
        sys.exit("%s: No such file or directory" % src)

    dst = os.path.join(outdir, dstname)
    if os.path.exists(dst) and \
        (os.path.samefile(src, dst) or
         os.path.samefile(os.path.dirname(src), dst)):
        sys.exit("%s: src and dst refer to same file" % src)

    shutil.copytree(src, dst, symlinks=True)

    return dst


# skip vcs files base on this pattern
METADATA_PATTERN = re.compile(r'.*/\.(bzr|git|hg|svn).*')


def create_tar(repodir, outdir, dstname, extension='tar',
               exclude=[], include=[], package_metadata=False):
    """Create a tarball of repodir in destination directory."""
    (workdir, topdir) = os.path.split(repodir)

    incl_patterns = []
    excl_patterns = []

    for i in include:
        # for backward compatibility add a trailing '*' if i isn't a pattern
        if fnmatch.translate(i) == i + fnmatch.translate(r''):
            i += r'*'

        pat = fnmatch.translate(os.path.join(topdir, i))
        incl_patterns.append(re.compile(pat))

    for e in exclude:
        excl_patterns.append(re.compile(fnmatch.translate(e)))

    def tar_exclude(filename):
        """Exclude (return True) or add (return False) file to tar achive."""
        if not package_metadata and METADATA_PATTERN.match(filename):
            return True

        if incl_patterns:
            for pat in incl_patterns:
                if pat.match(filename):
                    return False
            return True

        for pat in excl_patterns:
            if pat.match(filename):
                return True
        return False

    def reset(tarinfo):
        """Python 2.7 only: reset uid/gid to 0/0 (root)."""
        tarinfo.uid = tarinfo.gid = 0
        tarinfo.uname = tarinfo.gname = "root"
        return tarinfo

    def tar_filter(tarinfo):
        if tar_exclude(tarinfo.name):
            return None

        return reset(tarinfo)

    cwd = os.getcwd()
    os.chdir(workdir)

    tar = tarfile.open(os.path.join(outdir, dstname + '.' + extension), "w")
    try:
        tar.add(topdir, recursive=False, filter=reset)
    except TypeError:
        # Python 2.6 compatibility
        tar.add(topdir, recursive=False)
    for entry in map(lambda x: os.path.join(topdir, x), os.listdir(topdir)):
        try:
            tar.add(entry, filter=tar_filter)
        except TypeError:
            # Python 2.6 compatibility
            tar.add(entry, exclude=tar_exclude)
    tar.close()

    os.chdir(cwd)


CLEANUP_DIRS = []


def cleanup(dirs):
    """Cleaning temporary directories."""
    logging.info("Cleaning: %s", ' '.join(dirs))

    for d in dirs:
        if not os.path.exists(d):
            continue
        shutil.rmtree(d)


def version_iso_cleanup(version):
    """Reformat timestamp value."""
    version = re.sub(r'([0-9]{4})-([0-9]{2})-([0-9]{2}) +'
                     r'([0-9]{2})([:]([0-9]{2})([:]([0-9]{2}))?)?'
                     r'( +[-+][0-9]{3,4})', r'\1\2\3T\4\6\8', version)
    version = re.sub(r'[-:]', '', version)
    return version


def get_version(args, clone_dir):
    version = args.version
    if version == '_auto_' or args.versionformat:
        version = detect_version(args.scm, clone_dir, args.versionformat)
    if args.versionprefix:
        version = "%s.%s" % (args.versionprefix, version)

    logging.debug("VERSION(auto): %s", version)
    return version


def detect_version_git(repodir, versionformat):
    """Automatic detection of version number for checked-out GIT repository."""
    if versionformat is None:
        versionformat = '%ct.%h'

    if re.match('.*@PARENT_TAG@.*', versionformat):
        try:
            text = safe_run(['git', 'describe', '--tags', '--abbrev=0'],
                            repodir)[1]
            versionformat = re.sub('@PARENT_TAG@', text, versionformat)
        except SystemExit:
            sys.exit(r'\e[0;31mThe git repository has no tags,'
                     r' thus @PARENT_TAG@ can not be expanded\e[0m')

    version = safe_run(['git', 'log', '-n1', '--date=short',
                        "--pretty=format:%s" % versionformat], repodir)[1]
    return version_iso_cleanup(version)


def detect_version_svn(repodir, versionformat):
    """Automatic detection of version number for checked-out SVN repository."""
    if versionformat is None:
        versionformat = '%r'

    svn_info = safe_run(['svn', 'info'], repodir)[1]

    version = ''
    match = re.search('Last Changed Rev: (.*)', svn_info, re.MULTILINE)
    if match:
        version = match.group(1).strip()
    return re.sub('%r', version, versionformat)


def detect_version_hg(repodir, versionformat):
    """Automatic detection of version number for checked-out HG repository."""
    if versionformat is None:
        versionformat = '{rev}'

    version = safe_run(['hg', 'id', '-n'], repodir)[1]

    # Mercurial internally stores commit dates in its changelog
    # context objects as (epoch_secs, tz_delta_to_utc) tuples (see
    # mercurial/util.py).  For example, if the commit was created
    # whilst the timezone was BST (+0100) then tz_delta_to_utc is
    # -3600.  In this case,
    #
    #     hg log -l1 -r$rev --template '{date}\n'
    #
    # will result in something like '1375437706.0-3600' where the
    # first number is timezone-agnostic.  However, hyphens are not
    # permitted in rpm version numbers, so tar_scm removes them via
    # sed.  This is required for this template format for any time
    # zone "numerically east" of UTC.
    #
    # N.B. since the extraction of the timestamp as a version number
    # is generally done in order to provide chronological sorting,
    # ideally we would ditch the second number.  However the
    # template format string is left up to the author of the
    # _service file, so we can't do it here because we don't know
    # what it will expand to.  Mercurial provides template filters
    # for dates (e.g. 'hgdate') which _service authors could
    # potentially use, but unfortunately none of them can easily
    # extract only the first value from the tuple, except for maybe
    # 'sub(...)' which is only available since 2.4 (first introduced
    # in openSUSE 12.3).

    version = safe_run(['hg', 'log', '-l1', "-r%s" % version.strip(),
                        '--template', versionformat], repodir)[1]
    return version_iso_cleanup(version)


def detect_version_bzr(repodir, versionformat):
    """Automatic detection of version number for checked-out BZR repository."""
    if versionformat is None:
        versionformat = '%r'

    version = safe_run(['bzr', 'revno'], repodir)[1]
    return re.sub('%r', version.strip(), versionformat)


def detect_version(scm, repodir, versionformat=None):
    """Automatic detection of version number for checked-out repository."""
    detect_version_commands = {
        'git': detect_version_git,
        'svn': detect_version_svn,
        'hg':  detect_version_hg,
        'bzr': detect_version_bzr,
    }

    version = detect_version_commands[scm](repodir, versionformat).strip()
    logging.debug("VERSION(auto): %s", version)
    return version


def get_repocache_hash(scm, url, subdir):
    """Calculate hash fingerprint for repository cache."""
    digest = hashlib.new('sha256')
    digest.update(url)
    if scm == 'svn':
        digest.update('/' + subdir)
    return digest.hexdigest()


def import_xml_parser():
    """Import the best XML parser available.  Currently prefers lxml and
    falls back to xml.etree.

    There are some important differences in behaviour, which also
    depend on the Python version being used:

    | Python    | 2.6            | 2.6         | 2.7            | 2.7         |
    |-----------+----------------+-------------+----------------+-------------|
    | module    | lxml.etree     | xml.etree   | lxml.etree     | xml.etree   |
    |-----------+----------------+-------------+----------------+-------------|
    | empty     | XMLSyntaxError | ExpatError  | XMLSyntaxError | ParseError  |
    | doc       | "Document is   | "no element | "Document is   | "no element |
    |           | empty"         | found"      | empty          | found"      |
    |-----------+----------------+-------------+----------------+-------------|
    | syntax    | XMLSyntaxError | ExpatError  | XMLSyntaxError | ParseError  |
    | error     | "invalid       | "not well-  | "invalid       | "not well-  |
    |           | element name"  | formed"     | element name"  | formed"     |
    |-----------+----------------+-------------+----------------+-------------|
    | e.message | deprecated     | deprecated  | yes            | yes         |
    |-----------+----------------+-------------+----------------+-------------|
    | str()     | yes            | yes         | yes            | yes         |
    |-----------+----------------+-------------+----------------+-------------|
    | @attr     | yes            | no          | yes            | yes         |
    | selection |                |             |                |             |
    """
    global ET

    try:
        # If lxml is available, we can use a parser that doesn't
        # destroy comments
        import lxml.etree as ET
        xml_parser = ET.XMLParser(remove_comments=False)
    except ImportError:
        import xml.etree.ElementTree as ET
        xml_parser = None
        if not hasattr(ET, 'ParseError'):
            try:
                import xml.parsers.expat
            except:
                raise RuntimeError("Couldn't load XML parser error class")

    return xml_parser


def parse_servicedata_xml(srcdir):
    """Parses the XML in _servicedata.  Returns None if the file doesn't
    exist or is empty, or the ElementTree on successful parsing, or
    raises any other exception generated by parsing.
    """
    # Even if there's no _servicedata, we'll need the module later.
    xml_parser = import_xml_parser()

    servicedata_file = os.path.join(srcdir, "_servicedata")
    if not os.path.exists(servicedata_file):
        return None

    try:
        return ET.parse(servicedata_file, parser=xml_parser)
    except StandardError as e:
        # Tolerate an empty file, but any other parse error should be
        # made visible.
        if str(e).startswith("Document is empty") or \
           str(e).startswith("no element found"):
            return None
        raise


def extract_tar_scm_service(root, url):
    """Returns an object representing the <service name="tar_scm">
    element referencing the given URL.
    """
    try:
        tar_scm_services = root.findall("service[@name='tar_scm']")
    except SyntaxError:
        raise RuntimeError(
            "Couldn't load an XML parser supporting attribute selection. "
            "Try installing lxml.")

    for service in tar_scm_services:
        for param in service.findall("param[@name='url']"):
            if param.text == url:
                return service


def get_changesrevision(tar_scm_service):
    """Returns an object representing the <param name="changesrevision">
    element, or None, if it doesn't exist.
    """
    params = tar_scm_service.findall("param[@name='changesrevision']")
    if len(params) == 0:
        return None
    if len(params) > 1:
        raise RuntimeError('Found multiple <param name="changesrevision"> '
                           'elements in _servicedata.')
    return params[0]


def read_changes_revision(url, srcdir, outdir):
    """Reads the _servicedata file and returns a dictionary with 'revision' on
    success. As a side-effect it creates the _servicedata file if it doesn't
    exist. 'revision' is None in that case.
    """
    write_servicedata = False

    xml_tree = parse_servicedata_xml(srcdir)
    if xml_tree is None:
        root = ET.fromstring("<servicedata>\n</servicedata>\n")
        write_servicedata = True
    else:
        root = xml_tree.getroot()

    service = extract_tar_scm_service(root, url)
    if service is None:
        service = ET.fromstring("""\
          <service name="tar_scm">
            <param name="url">%s</param>
          </service>
        """ % url)
        root.append(service)
        write_servicedata = True

    if write_servicedata:
        ET.ElementTree(root).write(os.path.join(outdir, "_servicedata"))
    else:
        if not os.path.exists(os.path.join(outdir, "_servicedata")) or \
           not os.path.samefile(os.path.join(srcdir, "_servicedata"),
                                os.path.join(outdir, "_servicedata")):
            shutil.copy(os.path.join(srcdir, "_servicedata"),
                        os.path.join(outdir, "_servicedata"))

    change_data = {
        'revision': None
    }
    changesrevision_element = get_changesrevision(service)
    if changesrevision_element is not None:
        change_data['revision'] = changesrevision_element.text
    return change_data


def write_changes_revision(url, outdir, new_revision):
    """Updates the changesrevision in the _servicedata file."""
    logging.debug("Updating %s", os.path.join(outdir, '_servicedata'))

    xml_tree = parse_servicedata_xml(outdir)
    root = xml_tree.getroot()
    tar_scm_service = extract_tar_scm_service(root, url)
    if tar_scm_service is None:
        sys.exit("File _servicedata is missing tar_scm with URL '%s'" % url)

    changed = False
    element = get_changesrevision(tar_scm_service)
    if element is None:
        changed = True
        changesrevision = ET.fromstring(
            "    <param name=\"changesrevision\">%s</param>\n"
            % new_revision)
        tar_scm_service.append(changesrevision)
    elif element.text != new_revision:
        element.text = new_revision
        changed = True

    if changed:
        xml_tree.write(os.path.join(outdir, "_servicedata"))


def write_changes(changes_filename, changes, version, author):
    """Add changes to given *.changes file."""
    if changes is None:
        return

    logging.debug("Writing changes file %s", changes_filename)

    tmp_fp = tempfile.NamedTemporaryFile(delete=False)
    tmp_fp.write('-' * 67 + '\n')
    tmp_fp.write("%s - %s\n" % (
        datetime.datetime.utcnow().strftime('%a %b %d %H:%M:%S UTC %Y'),
        author))
    tmp_fp.write('\n')
    tmp_fp.write("- Update to version %s:\n" % version)
    for line in changes:
        tmp_fp.write("  + %s\n" % line)
    tmp_fp.write('\n')

    old_fp = open(changes_filename, 'r')
    tmp_fp.write(old_fp.read())
    old_fp.close()

    tmp_fp.close()

    shutil.move(tmp_fp.name, changes_filename)


def detect_changes_commands_git(repodir, changes):
    """Detect changes between GIT revisions."""
    last_rev = changes['revision']

    if last_rev is None:
        last_rev = safe_run(['git', 'log', '-n1', '--pretty=format:%H',
                             '--skip=10'], cwd=repodir)[1]
    current_rev = safe_run(['git', 'log', '-n1', '--pretty=format:%H'],
                           cwd=repodir)[1]

    if last_rev == current_rev:
        logging.debug("No new commits, skipping changes file generation")
        return

    logging.debug("Generating changes between %s and %s", last_rev,
                  current_rev)

    lines = safe_run(['git', 'log',
                      '--reverse', '--no-merges', '--pretty=format:%s',
                      "%s..%s" % (last_rev, current_rev)], repodir)[1]

    changes['revision'] = current_rev
    changes['lines'] = lines.split('\n')
    return changes


def detect_changes(scm, url, repodir, outdir):
    """Detect changes between revisions."""
    changes = read_changes_revision(url, os.getcwd(), outdir)

    logging.debug("CHANGES: %s" % repr(changes))

    detect_changes_commands = {
        'git': detect_changes_commands_git,
    }

    if scm not in detect_changes_commands:
        sys.exit("changesgenerate not supported with %s SCM" % scm)

    changes = detect_changes_commands[scm](repodir, changes)
    logging.debug("Detected changes:\n%s" % repr(changes))
    return changes


def get_changesauthor(args):
    if args.changesauthor:
        return args.changesauthor

    config = ConfigParser.RawConfigParser()
    obs = 'https://api.opensuse.org'
    config.add_section(obs)
    config.set(obs, 'email', DEFAULT_AUTHOR)
    config.read(os.path.expanduser('~/.oscrc'))
    changesauthor = config.get('https://api.opensuse.org', 'email')

    logging.debug("AUTHOR: %s", changesauthor)
    return changesauthor


def get_config_options():
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
    for opt in config.options('tar_scm'):
        config.set('tar_scm', opt, re.sub(r'"(.*)"', r'\1',
                                          config.get('tar_scm', opt)))

    return config


def parse_args():
    parser = argparse.ArgumentParser(description='Git Tarballs')
    parser.add_argument('-v', '--verbose', action='store_true', default=False,
                        help='Enable verbose output')
    parser.add_argument('--scm', required=True,
                        help='Specify SCM',
                        choices=['git', 'hg', 'bzr', 'svn'])
    parser.add_argument('--url', required=True,
                        help='Specify URL of upstream tarball to download')
    parser.add_argument('--version', default='_auto_',
                        help='Specify version to be used in tarball. '
                             'Defaults to automatically detected value '
                             'formatted by versionformat parameter.')
    parser.add_argument('--versionformat',
                        help='Auto-generate version from checked out source '
                             'using this format string.  This parameter is '
                             'used if the \'version\' parameter is not '
                             'specified.')
    parser.add_argument('--versionprefix',
                        help='Specify a base version as prefix.')
    parser.add_argument('--revision',
                        help='Specify revision to package')
    parser.add_argument('--filename',
                        help='Name of package - used together with version '
                             'to determine tarball name')
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
                             DEFAULT_AUTHOR)
    parser.add_argument('--subdir', default='',
                        help='Package just a subdirectory of the sources')
    parser.add_argument('--submodules', choices=['enable', 'disable'],
                        default='enable',
                        help='Whether or not to include git submodules '
                             'from SCM commit log since a given parent '
                             'revision (see changesrevision).')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--include', action='append',
                       default=[], metavar='REGEXP',
                       help='Specifies subset of files/subdirectories to '
                            'pack in the tarball (can be repeated)')
    group.add_argument('--exclude', action='append',
                       default=[], metavar='REGEXP',
                       help='Specifies excludes when creating the '
                            'tarball (can be repeated)')
    parser.add_argument('--package-meta', choices=['yes', 'no'], default='no',
                        help='Package the meta data of SCM to allow the user '
                             'or OBS to update after un-tar')
    parser.add_argument('--outdir', required=True,
                        help='osc service parameter for internal use only '
                             '(determines where generated files go before '
                             'collection')
    parser.add_argument('--history-depth',
                        help='Obsolete osc service parameter that does '
                             'nothing')
    args = parser.parse_args()

    # basic argument validation
    if not os.path.isdir(args.outdir):
        sys.exit("%s: No such directory" % args.outdir)

    if args.history_depth:
        print "history-depth parameter is obsolete and will be ignored"

    # booleanize non-standard parameters
    if args.changesgenerate == 'enable':
        args.changesgenerate = True
    else:
        args.changesgenerate = False

    if args.package_meta == 'yes':
        args.package_meta = True
    else:
        args.package_meta = False

    if args.submodules == 'enable':
        args.submodules = True
    else:
        args.submodules = False

    # force verbose mode in test-mode
    if os.getenv('DEBUG_TAR_SCM'):
        args.verbose = True

    return args


def get_repocachedir():
    # check for enabled caches (1. environment, 2. user config, 3. system wide)
    repocachedir = os.getenv('CACHEDIRECTORY')
    if repocachedir is None:
        config = get_config_options()
        try:
            repocachedir = config.get('tar_scm', 'CACHEDIRECTORY')
        except ConfigParser.Error:
            pass

    if repocachedir:
        logging.debug("REPOCACHE: %s", repocachedir)

    return repocachedir


def main():
    args = parse_args()

    FORMAT = "%(message)s"
    logging.basicConfig(format=FORMAT, stream=sys.stderr, level=logging.INFO)
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # force cleaning of our workspace on exit
    atexit.register(cleanup, CLEANUP_DIRS)

    repocachedir = get_repocachedir()

    # construct repodir (the parent directory of the checkout)
    repodir = None
    if repocachedir and os.path.isdir(os.path.join(repocachedir, 'repo')):
        repohash = get_repocache_hash(args.scm, args.url, args.subdir)
        logging.debug("HASH: %s", repohash)
        repodir = os.path.join(repocachedir, 'repo')
        repodir = os.path.join(repodir, repohash)

    # if caching is enabled but we haven't cached something yet
    if repodir and not os.path.isdir(repodir):
        repodir = tempfile.mkdtemp(dir=os.path.join(repocachedir, 'incoming'))

    if repodir is None:
        repodir = tempfile.mkdtemp(dir=args.outdir)
        CLEANUP_DIRS.append(repodir)

    clone_dir = fetch_upstream(out_dir=repodir, **args.__dict__)

    if args.filename:
        dstname = args.filename
    else:
        dstname = os.path.basename(clone_dir)

    version = get_version(args, clone_dir)
    changesversion = version
    if version:
        dstname += '-' + version

    logging.debug("DST: %s", dstname)

    changes = None
    if args.changesgenerate:
        changes = detect_changes(args.scm, args.url, clone_dir, args.outdir)

    tar_dir = prep_tree_for_tar(clone_dir, args.subdir, args.outdir,
                                dstname=dstname)
    CLEANUP_DIRS.append(tar_dir)

    create_tar(tar_dir, args.outdir,
               dstname=dstname, extension=args.extension,
               exclude=args.exclude, include=args.include,
               package_metadata=args.package_meta)

    if changes:
        changesauthor = get_changesauthor(args)

        logging.debug("AUTHOR: %s", changesauthor)

        if not version:
            args.version = "_auto_"
            changesversion = get_version(args, clone_dir)

        for filename in glob.glob('*.changes'):
            new_changes_file = os.path.join(args.outdir, filename)
            shutil.copy(filename, new_changes_file)
            write_changes(new_changes_file, changes['lines'],
                          changesversion, changesauthor)
        write_changes_revision(args.url, args.outdir,
                               changes['revision'])

    # Populate cache
    if repocachedir and os.path.isdir(os.path.join(repocachedir, 'repo')):
        repodir2 = os.path.join(repocachedir, 'repo')
        repodir2 = os.path.join(repodir2, repohash)
        if repodir2 and not os.path.isdir(repodir2):
            os.rename(repodir, repodir2)
        elif not os.path.samefile(repodir, repodir2):
            CLEANUP_DIRS.append(repodir)

if __name__ == '__main__':
    main()
