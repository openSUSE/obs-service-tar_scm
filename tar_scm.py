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
import dateutil.parser

try:
    # not possible to test this on travis atm
    import yaml
except ImportError:
    pass

from urlparse import urlparse


class TarSCM:
    class scm():
        def __init__(self,**kwargs):
            self.scm      = self.__class__.__name__
            self.url      = kwargs['url']
            self.helpers  = TarSCM.helpers()
            self.repocachedir = None

        def switch_revision(self,clone_dir, revision):
            """Switch sources to revision. Dummy implementation for version control
            systems that change revision during fetch/update.
            """
            return

        def fetch_upstream(self, revision, out_dir, **kwargs):
            """Fetch sources from repository and checkout given revision."""
            logging.debug("SCM: '%s'" % self.scm)
            clone_prefix = ""
            if 'clone_prefix' in kwargs:
                clone_prefix = kwargs['clone_prefix']
            clone_dir = self._calc_dir_to_clone_to(clone_prefix, out_dir)

            if not os.path.isdir(clone_dir):
                # initial clone
                os.mkdir(clone_dir)
                self.fetch_upstream_scm( clone_dir, revision, cwd=out_dir,
                                          kwargs=kwargs)
            else:
                logging.info("Detected cached repository...")
                self.update_cache(clone_dir, revision)
            
            # switch_to_revision
            self.switch_revision(clone_dir, revision)

            # git specific: after switching to desired revision its necessary to update
            # submodules since they depend on the actual version of the selected
            # revision
            self.fetch_submodules(clone_dir, kwargs)

            return clone_dir

        def fetch_submodules(self, clone_dir, kwargs):
            """NOOP in other scm's than git"""
            pass

        def detect_changes(self, args, clone_dir):
            """Detect changes between revisions."""
            if (not args.changesgenerate):
                return None

            changes = read_changes_revision(self.url, os.getcwd(), args.outdir)

            logging.debug("CHANGES: %s" % repr(changes))

            changes = self.detect_changes_scm(clone_dir, args.subdir, changes)
            logging.debug("Detected changes:\n%s" % repr(changes))
            return changes

        def detect_changes_scm(self, repodir, subdir, changes):
            sys.exit("changesgenerate not supported with %s SCM" % self.scm)

        def get_repocache_hash(self, subdir):
            """Calculate hash fingerprint for repository cache."""
            return hashlib.sha256(self.url).hexdigest()

        def get_current_commit(self, clone_dir):
            return None

        def get_repocachedir(self):
            # check for enabled caches in this order (first wins):
            #   1. local .cache
            #   2. environment
            #   3. user config
            #   4. system wide
            cwd = os.getcwd()
            if self.repocachedir is None:
                if os.path.isdir(os.path.join(cwd, '.cache')):
                    self.repocachedir = os.path.join(cwd, '.cache')

            if self.repocachedir is None:
                self.repocachedir = os.getenv('CACHEDIRECTORY')

            if self.repocachedir is None:
                config = get_config_options()
                try:
                    self.repocachedir = config.get('tar_scm', 'CACHEDIRECTORY')
                except ConfigParser.Error:
                    pass

            if self.repocachedir:
                logging.debug("REPOCACHE: %s", self.repocachedir)

            return self.repocachedir

        def _calc_dir_to_clone_to(self, prefix, out_dir):
            # separate path from parameters etc.
            url_path = urlparse(self.url)[2].rstrip('/')

            # remove trailing scm extension
            url_path = re.sub(r'\.%s$' % self.scm, '', url_path)

            # special handling for cloning bare repositories (../repo/.git/)
            url_path = url_path.rstrip('/')

            basename = os.path.basename(os.path.normpath(url_path))
            basename = prefix + basename
            clone_dir = os.path.abspath(os.path.join(out_dir, basename))
            return clone_dir
    ### END class TarSCM.scm

    class git(scm):
        def switch_revision(self,clone_dir, revision):
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

            found_revision = None
            revs = [x + revision for x in ['origin/', '']]
            for rev in revs:
                if self._ref_exists(clone_dir, rev):
                    found_revision = True
                    if os.getenv('OSC_VERSION'):
                        stash_text = self.helpers.safe_run(['git', 'stash'], cwd=clone_dir)[1]
                        text = self.helpers.safe_run(['git', 'reset', '--hard', rev],
                                        cwd=clone_dir)[1]
                        if stash_text != "No local changes to save\n":
                            text += self.helpers.safe_run(['git', 'stash', 'pop'],
                                             cwd=clone_dir)[1]
                    else:
                        text = self.helpers.safe_run(['git', 'reset', '--hard', rev],
                                        cwd=clone_dir)[1]
                    print text.rstrip()
                    break

            if found_revision is None:
                sys.exit('%s: No such revision' % revision)

            # only update submodules if they have been enabled
            if os.path.exists(
                    os.path.join(clone_dir, os.path.join('.git', 'modules'))):
                self.helpers.safe_run(['git', 'submodule', 'update', '--recursive'], cwd=clone_dir)

        def fetch_upstream_scm(self, clone_dir, revision, cwd, kwargs):
            """SCM specific version of fetch_uptream for git."""
            command = ['git', 'clone', self.url, clone_dir]

            if not is_sslverify_enabled(kwargs):
                command += ['--config', 'http.sslverify=false']
            self.helpers.safe_run(command, cwd=cwd, interactive=sys.stdout.isatty())
            # if the reference does not exist.
            if revision and not self._ref_exists(clone_dir, revision):
                # fetch reference from url and create locally
                self.helpers.safe_run(['git', 'fetch', self.url, revision + ':' + revision],
                         cwd=clone_dir, interactive=sys.stdout.isatty())

        def fetch_submodules(self, clone_dir, kwargs):
            """Recursively initialize git submodules."""
            if 'submodules' in kwargs and kwargs['submodules'] == 'enable':
                self.helpers.safe_run(['git', 'submodule', 'update', '--init', '--recursive'],
                         cwd=clone_dir)
            elif 'submodules' in kwargs and kwargs['submodules'] == 'master':
                self.helpers.safe_run(['git', 'submodule', 'update', '--init', '--recursive',
                         '--remote'], cwd=clone_dir)

        def update_cache(self, clone_dir, revision):
            """Update sources via git."""
            self.helpers.safe_run(['git', 'fetch', '--tags'],
                     cwd=clone_dir, interactive=sys.stdout.isatty())
            self.helpers.safe_run(['git', 'fetch'],
                     cwd=clone_dir, interactive=sys.stdout.isatty())

        def detect_version(self, args, repodir):
            """Automatic detection of version number for checked-out GIT repository."""
            parent_tag = args['parent_tag']
            versionformat = args['versionformat']
            if versionformat is None:
                versionformat = '%ct.%h'

            if not parent_tag:
                rc, output = self.helpers.run_cmd(['git', 'describe', '--tags', '--abbrev=0'],
                                     repodir)
                if rc == 0:
                    # strip to remove newlines
                    parent_tag = output.strip()
            if re.match('.*@PARENT_TAG@.*', versionformat):
                if parent_tag:
                    if args.get('tagpattern') and args.get('tagrepl'):
                        parent_tag = re.sub(args['tagpattern'], args['tagrepl'], parent_tag)
                    versionformat = re.sub('@PARENT_TAG@', parent_tag, versionformat)
                else:
                    sys.exit("\033[31mNo parent tag present for the checked out "
                             "revision, thus @PARENT_TAG@ cannot be expanded.\033[0m")

            if re.match('.*@TAG_OFFSET@.*', versionformat):
                if parent_tag:
                    rc, output = self.helpers.run_cmd(['git', 'rev-list', '--count',
                                          parent_tag + '..HEAD'], repodir)
                    if not rc:
                        tag_offset = output.strip()
                        versionformat = re.sub('@TAG_OFFSET@', tag_offset,
                                               versionformat)
                    else:
                        sys.exit("\033[31m@TAG_OFFSET@ can not be expanded: " +
                                 output + "\033[0m")
                else:
                    sys.exit("\033[31m@TAG_OFFSET@ cannot be expanded, "
                             "as no parent tag was discovered.\033[0m")

            version = self.helpers.safe_run(['git', 'log', '-n1', '--date=short',
                                "--pretty=format:%s" % versionformat], repodir)[1]
            return version_iso_cleanup(version)

        def get_timestamp(self, args, repodir):
            d = {"parent_tag": None, "versionformat": "%ct"}
            timestamp = self.detect_version(d, repodir)
            return int(timestamp)

        def get_current_commit(self, clone_dir):
            return  self.helpers.safe_run(['git', 'rev-parse', 'HEAD'], clone_dir)[1]

        def _ref_exists(self, clone_dir, revision):
            rc, _ = self.helpers.run_cmd(['git', 'rev-parse', '--verify', '--quiet', revision],
                            cwd=clone_dir, interactive=sys.stdout.isatty())
            return (rc == 0)

        def _log_cmd(self, cmd_args, repodir, subdir):
            """ Helper function to call 'git log' with args"""
            cmd = ['git', 'log'] + cmd_args
            if subdir:
                cmd += ['--', subdir]
            return self.helpers.safe_run(cmd, cwd=repodir)[1]


        def detect_changes_scm(self, clone_dir, subdir, changes):
            """Detect changes between GIT revisions."""
            last_rev = changes['revision']

            if last_rev is None:
                last_rev = self._log_cmd(['-n1', '--pretty=format:%H', '--skip=10'],
                                        clone_dir, subdir)
            current_rev = self._log_cmd(['-n1', '--pretty=format:%H'], clone_dir, subdir)

            if last_rev == current_rev:
                logging.debug("No new commits, skipping changes file generation")
                return

            dbg_msg = "Generating changes between %s and %s" % (last_rev, current_rev)
            if subdir:
                dbg_msg += " (for subdir: %s)" % (subdir)
            logging.debug(dbg_msg)

            lines = self._log_cmd(['--reverse', '--no-merges', '--pretty=format:%s',
                                  "%s..%s" % (last_rev, current_rev)], clone_dir, subdir)

            changes['revision'] = current_rev
            changes['lines'] = lines.split('\n')
            return changes
    ### END class TarSCM.git

    class hg(scm):
        def switch_revision(self,clone_dir, revision):
            """Switch sources to revision."""
            if revision is None:
                revision = 'tip'

            rc, _  = self.helpers.run_cmd(['hg', 'update', revision], cwd=clone_dir,
                             interactive=sys.stdout.isatty())
            if rc:
                sys.exit('%s: No such revision' % revision)

        def fetch_upstream_scm(self, clone_dir, revision, cwd, kwargs):
            """SCM specific version of fetch_uptream for hg."""
            command = ['hg', 'clone', self.url, clone_dir]
            if not is_sslverify_enabled(kwargs):
                command += ['--insecure']
            self.helpers.safe_run(command, cwd,
                     interactive=sys.stdout.isatty())

        def update_cache(self, clone_dir, revision):
            """Update sources via hg."""
            try:
                self.helpers.safe_run(['hg', 'pull'], cwd=clone_dir,
                         interactive=sys.stdout.isatty())
            except SystemExit, e:
                # Contrary to the docs, hg pull returns exit code 1 when
                # there are no changes to pull, but we don't want to treat
                # this as an error.
                if re.match('.*no changes found.*', e.message) is None:
                    raise

        def detect_version(self, args, repodir):
            """Automatic detection of version number for checked-out HG repository."""
            parent_tag = args['parent_tag']
            versionformat = args['versionformat']
            if versionformat is None:
                versionformat = '{rev}'

            version = self.helpers.safe_run(['hg', 'id', '-n'], repodir)[1]

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

            version = self.helpers.safe_run(['hg', 'log', '-l1', "-r%s" % version.strip(),
                                '--template', versionformat], repodir)[1]
            return version_iso_cleanup(version)

        def get_timestamp(self, args, repodir):
            d = {"parent_tag": None, "versionformat": "{date}"}
            timestamp = self.detect_version(d, repodir)
            timestamp = re.sub(r'([0-9]+)\..*', r'\1', timestamp)
            return int(timestamp)
    ### END class TarSCM.hg

    class svn(scm):
        def fetch_upstream_scm(self, clone_dir, revision, cwd, kwargs):
            """SCM specific version of fetch_uptream for svn."""
            command = ['svn', 'checkout', '--non-interactive', self.url, clone_dir]
            if revision:
                command.insert(4, '-r%s' % revision)
            if not is_sslverify_enabled(kwargs):
                command.insert(3, '--trust-server-cert')
            self.helpers.safe_run(command, cwd, interactive=sys.stdout.isatty())

        def update_cache(self, clone_dir, revision):
            """Update sources via svn."""
            command = ['svn', 'update']
            if revision:
                command.insert(3, "-r%s" % revision)
            self.helpers.safe_run(command, cwd=clone_dir, interactive=sys.stdout.isatty())

        def detect_version(self, args, repodir):
            """Automatic detection of version number for checked-out SVN repository."""
            versionformat = args['versionformat']
            if versionformat is None:
                versionformat = '%r'

            svn_info = self.helpers.safe_run(['svn', 'info'], repodir)[1]

            version = ''
            match = re.search('Last Changed Rev: (.*)', svn_info, re.MULTILINE)
            if match:
                version = match.group(1).strip()
            return re.sub('%r', version, versionformat)

        def get_timestamp(self, args, repodir):
            svn_info = self.helpers.safe_run(['svn', 'info', '-rHEAD'], repodir)[1]

            match = re.search('Last Changed Date: (.*)', svn_info, re.MULTILINE)
            if not match:
                return 0

            timestamp = match.group(1).strip()
            timestamp = re.sub('\(.*\)', '', timestamp)
            timestamp = dateutil.parser.parse(timestamp).strftime("%s")
            return int(timestamp)

        def detect_changes_scm(self, clone_dir, subdir, changes):
            """Detect changes between GIT revisions."""
            last_rev = changes['revision']
            first_run = False
            if subdir:
                clone_dir = os.path.join(clone_dir, subdir)

            if last_rev is None:
                last_rev = self._get_rev(clone_dir, 10)
                logging.debug("First run get log for initial release")
                first_run = True

            current_rev = self._get_rev(clone_dir, 1)

            if last_rev == current_rev:
                logging.debug("No new commits, skipping changes file generation")
                return

            if not first_run:
                # Increase last_rev by 1 so we dont get duplication of log messages
                last_rev = int(last_rev) + 1

            logging.debug("Generating changes between %s and %s", last_rev,
                          current_rev)
            lines = self._get_log(clone_dir, last_rev, current_rev)

            changes['revision'] = current_rev
            changes['lines'] = lines
            return changes

        def get_repocache_hash(self,subdir):
            """Calculate hash fingerprint for repository cache."""
            return hashlib.sha256(self.url+'/' + subdir).hexdigest()


        def _get_log(self, repodir, revision1, revision2):
            new_lines = []

            xml_lines = self.helpers.safe_run(['svn', 'log', '-r%s:%s' % (revision1,
                                 revision2), '--xml'], repodir)[1]
            lines = re.findall(r"<msg>.*?</msg>", xml_lines, re.S)

            for line in lines:
                line = line.replace("<msg>", "").replace("</msg>", "")
                new_lines = new_lines + line.split("\n")

            return new_lines


        def _get_rev(self, repodir, num_commits):
            revisions = self.helpers.safe_run(['svn', 'log', '-l%d' % num_commits, '-q',
                                 '--incremental'], cwd=repodir)[1].split('\n')
            # remove blank entry on end
            revisions.pop()
            # return last entry
            revision = revisions[-1]
            # retrieve the revision number and remove r
            revision = re.search(r'^r[0-9]*', revision, re.M).group().replace("r", "")
            return revision
    ### END class TarSCM.svn

    class bzr(scm):
        def fetch_upstream_scm(self, clone_dir, revision, cwd, kwargs):
            """SCM specific version of fetch_uptream for bzr."""
            command = ['bzr', 'checkout', self.url, clone_dir]
            if revision:
                command.insert(3, '-r')
                command.insert(4, revision)
            if not is_sslverify_enabled(kwargs):
                command.insert(2, '-Ossl.cert_reqs=None')
            self.helpers.safe_run(command, cwd, interactive=sys.stdout.isatty())

        def update_cache(self, clone_dir, revision):
            """Update sources via bzr."""
            command = ['bzr', 'update']
            if revision:
                command.insert(3, '-r')
                command.insert(4, revision)
            self.helpers.safe_run(command, cwd=clone_dir, interactive=sys.stdout.isatty())

        def detect_version(self, args, repodir):
            """Automatic detection of version number for checked-out BZR repository."""
            versionformat = args['versionformat']
            if versionformat is None:
                versionformat = '%r'

            version = self.helpers.safe_run(['bzr', 'revno'], repodir)[1]
            return re.sub('%r', version.strip(), versionformat)

        def get_timestamp(self, args, repodir):
            log = self.helpers.safe_run(['bzr', 'log', '--limit=1', '--log-format=long'],
                           repodir)[1]
            match = re.search(r'timestamp:(.*)', log, re.MULTILINE)
            if not match:
                return 0
            timestamp = dateutil.parser.parse(match.group(1).strip()).strftime("%s")
            return int(timestamp)
    ### END class TarSCM.bzr

    class tar(scm):
        def fetch_upstream(self, clone_dir, revision, cwd, kwargs):
            """SCM specific version of fetch_uptream for tar."""
            if kwargs.obsinfo is None:
                files = glob.glob('*.obsinfo')
                if len(files) > 0:
                    # or we refactor and loop about all on future
                    kwargs.obsinfo = files[0]
            if kwargs.obsinfo is None:
                sys.exit("ERROR: no .obsinfo file found")
            basename = clone_dir = read_from_obsinfo(args.obsinfo, "name")
            clone_dir += "-" + read_from_obsinfo(args.obsinfo, "version")
            if not os.path.exists(clone_dir):
                # not need in case of local osc build
                os.rename(basename, clone_dir)

            return clone_dir

        def update_cache(self, clone_dir, revision):
            """Update sources via tar."""
            pass

        def detect_version(self, args, repodir):
            """Read former stored version."""
            return read_from_obsinfo(args['obsinfo'], "version")

        def get_timestamp(self, args, repodir):
            return int(read_from_obsinfo(args.obsinfo, "mtime"))
    ### END class TarSCM.tar

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
    ### END class TarSCM.helpers

    class archive():
        def extract_from_archive(self, repodir, files, outdir):
            """Extract all files directly outside of the archive.
            """
            if files is None:
                return

            for filename in files:
                src = os.path.join(repodir, filename)
                if not os.path.exists(src):
                    sys.exit("%s: No such file or directory" % src)

                if shutil.copy(src, outdir):
                    sys.exit("%s: Failed to copy file" % src)


    ### END class TarSCM.archive
        class obscpio():
            def create_archive(self, scm_object, repodir, basename, dstname, version, commit, args):
                """Create an OBS cpio archive of repodir in destination directory.
                """
                (workdir, topdir) = os.path.split(repodir)
                extension = 'obscpio'

                cwd = os.getcwd()
                os.chdir(workdir)

                archivefilename = os.path.join(args.outdir, dstname + '.' + extension)
                archivefile = open(archivefilename, "w")
                proc = subprocess.Popen(['cpio', '--create', '--format=newc'],
                                        shell=False,
                                        stdin=subprocess.PIPE,
                                        stdout=archivefile)

                # transform glob patterns to regular expressions
                includes = r'|'.join([fnmatch.translate(x) for x in args.include])
                excludes = r'|'.join([fnmatch.translate(x) for x in args.exclude]) or r'$.'

                # add topdir without filtering for now
                for root, dirs, files in os.walk(topdir, topdown=False):
                    # excludes
                    dirs[:] = [os.path.join(root, d) for d in dirs]
                    dirs[:] = [d for d in dirs if not re.match(excludes, d)]

                    # exclude/include files
                    files = [os.path.join(root, f) for f in files]
                    files = [f for f in files if not re.match(excludes, f)]
                    files = [f for f in files if re.match(includes, f)]

                    for name in dirs:
                        proc.stdin.write(name)
                        proc.stdin.write("\n")
                    for name in files:
                        if not METADATA_PATTERN.match(name):
                            proc.stdin.write(name)
                            proc.stdin.write("\n")

                proc.stdin.close()
                ret_code = proc.wait()
                if ret_code != 0:
                    sys.exit("creating the cpio archive failed!")
                archivefile.close()

                # write meta data
                metafile = open(os.path.join(args.outdir, basename + '.obsinfo'), "w")
                metafile.write("name: " + basename + "\n")
                metafile.write("version: " + version + "\n")
                metafile.write("mtime: " + str(get_timestamp(scm_object, args, topdir)) + "\n")
                # metafile.write("git describe: " + + "\n")
                if commit:
                    metafile.write("commit: " + commit + "\n")
                metafile.close()

                os.chdir(cwd)
        ### END class TarSCM.archive.obscpio

        class tar():
            def create_archive(self, scm_object, repodir, outdir, dstname, extension='tar',
                           exclude=[], include=[], package_metadata=False, timestamp=0):
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
                    pat = fnmatch.translate(os.path.join(topdir, e))
                    excl_patterns.append(re.compile(pat))

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
                    if timestamp != 0:
                        tarinfo.mtime = timestamp
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
        ### END class TarSCM.archive.obscpio

def is_sslverify_enabled(kwargs):
    """Returns ``True`` if the ``sslverify`` option has been enabled or
    not been set (default enabled) ``False`` otherwise."""
    return 'sslverify' not in kwargs or kwargs['sslverify']


FETCH_UPSTREAM_COMMANDS = {
    'git': 1,
    'svn': 1,
    'hg':  1,
    'bzr': 1,
}


def prep_tree_for_archive(repodir, subdir, outdir, dstname):
    """Prepare directory tree for creation of the archive by copying the
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
DEFAULT_AUTHOR = 'opensuse-packaging@opensuse.org'





CLEANUP_DIRS = []


def cleanup(dirs):
    """Cleaning temporary directories."""
    logging.debug("Cleaning: %s", ' '.join(dirs))

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


def get_version(scm_object, args, clone_dir):
    version = args.version
    if version == '_auto_' or args.versionformat:
        version = detect_version(scm_object, args, clone_dir)
    if args.versionprefix:
        version = "%s.%s" % (args.versionprefix, version)

    logging.debug("VERSION(auto): %s", version)
    return version


def read_from_obsinfo(filename, key):
    infofile = open(filename, "r")
    line = infofile.readline()
    while line:
        k = line.split(":", 1)
        if k[0] == key:
            return k[1].strip()
        line = infofile.readline()
    return ""


def detect_version(scm_object, args, repodir):
    """Automatic detection of version number for checked-out repository."""

    version = scm_object.detect_version(args.__dict__, repodir).strip()
    logging.debug("VERSION(auto): %s", version)
    return version


def get_timestamp(scm_object, args, clone_dir):
    """Returns the commit timestamp for checked-out repository."""

    timestamp = scm_object.get_timestamp(args, clone_dir)
    logging.debug("COMMIT TIMESTAMP: %s (%s)", timestamp,
                  datetime.datetime.fromtimestamp(timestamp).strftime(
                      '%Y-%m-%d %H:%M:%S'))
    return timestamp


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
        tmp_fp.write("  * %s\n" % line)
    tmp_fp.write('\n')

    old_fp = open(changes_filename, 'r')
    tmp_fp.write(old_fp.read())
    old_fp.close()

    tmp_fp.close()

    shutil.move(tmp_fp.name, changes_filename)


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
                        help='Auto-generate version from checked out source '
                             'using this format string.  This parameter is '
                             'used if the \'version\' parameter is not '
                             'specified.')
    parser.add_argument('--tagpattern',
                        help='re.sub pattern to match and group version '
                             'in @PARENT_TAG@')
    parser.add_argument('--tagrepl',
                        help='re.sub repl to replace matched '
                             'in @PARENT_TAG@')
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

    args.outdir = os.path.abspath(args.outdir)
    orig_subdir = args.subdir
    args.subdir = os.path.normpath(orig_subdir)
    if args.subdir.startswith('/'):
        sys.exit("Absolute path '%s' is not allowed for --subdir" %
                 orig_subdir)
    if args.subdir == '..' or args.subdir.startswith('../'):
        sys.exit("--subdir path '%s' must stay within repo" % orig_subdir)

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

    args.sslverify = False if args.sslverify == 'disable' else True

    # force verbose mode in test-mode
    if os.getenv('DEBUG_TAR_SCM'):
        args.verbose = True

    return args




def main():
    args = parse_args()

    if sys.argv[0].endswith("tar"):
        args.scm = "tar"

    use_obs_scm = None
    if sys.argv[0].endswith("obs_scm"):
        use_obs_scm = True

    if sys.argv[0].endswith("snapcraft"):
        # we read the SCM config from snapcraft.yaml instead from _service file
        f = open('snapcraft.yaml')
        dataMap = yaml.safe_load(f)
        f.close()
        # run for each part an own task
        for part in dataMap['parts'].keys():
            args.filename = part
            if 'source-type' not in dataMap['parts'][part].keys():
                continue
            pep8_1 = dataMap['parts'][part]['source-type']
            pep8_2 = FETCH_UPSTREAM_COMMANDS.keys()
            if pep8_1 not in pep8_2:
                continue
            # avoid conflicts with files
            args.clone_prefix = "_obs_"
            args.url = dataMap['parts'][part]['source']
            dataMap['parts'][part]['source'] = part
            args.scm = dataMap['parts'][part]['source-type']
            del dataMap['parts'][part]['source-type']
            singletask(True, args)

        # write the new snapcraft.yaml file
        # we prefix our own here to be sure to not overwrite user files, if he
        # is using us in "disabled" mode
        new_file = args.outdir + '/_service:snapcraft:snapcraft.yaml'
        with open(new_file, 'w') as outfile:
            outfile.write(yaml.dump(dataMap, default_flow_style=False))
    else:
        singletask(use_obs_scm, args)


def singletask(use_obs_scm, args):
    FORMAT  = "%(message)s"
    logging.basicConfig(format=FORMAT, stream=sys.stderr, level=logging.INFO)
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # force cleaning of our workspace on exit
    atexit.register(cleanup, CLEANUP_DIRS)

    # create objects for TarSCM.<scm> and TarSCM.helpers
    scm_class    = getattr(TarSCM,args.scm)
    scm_object   = scm_class(url=args.url)
    helpers      = scm_object.helpers

    repocachedir = scm_object.get_repocachedir()

    repodir = None
    # construct repodir (the parent directory of the checkout)
    if repocachedir and os.path.isdir(repocachedir):
        # construct subdirs on very first run
        if not os.path.isdir(os.path.join(repocachedir, 'repo')):
            os.mkdir(os.path.join(repocachedir, 'repo'))
        if not os.path.isdir(os.path.join(repocachedir, 'incoming')):
            os.mkdir(os.path.join(repocachedir, 'incoming'))

        repohash = scm_object.get_repocache_hash(args.subdir)
        logging.debug("HASH: %s", repohash)
        repodir = os.path.join(repocachedir, 'repo', repohash)

    # if caching is enabled but we haven't cached something yet
    if repodir and not os.path.isdir(repodir):
        repodir = tempfile.mkdtemp(dir=os.path.join(repocachedir, 'incoming'))

    if repodir is None:
        repodir = tempfile.mkdtemp(dir=args.outdir)
        CLEANUP_DIRS.append(repodir)

    # special case when using osc and creating an obscpio, use current work
    # directory to allow the developer to work inside of the git repo and fetch
    # local changes
    if sys.argv[0].endswith("snapcraft") or \
       (use_obs_scm and os.getenv('OSC_VERSION')):
        repodir = os.getcwd()

    clone_dir = scm_object.fetch_upstream(out_dir=repodir, **args.__dict__)

    if args.filename:
        dstname = basename = args.filename
    else:
        dstname = basename = os.path.basename(clone_dir)

    version = get_version(scm_object, args, clone_dir)
    changesversion = version
    if version and not sys.argv[0].endswith("/tar") \
       and not sys.argv[0].endswith("/snapcraft"):
        dstname += '-' + version

    logging.debug("DST: %s", dstname)

    changes = scm_object.detect_changes(args,clone_dir)

    tar_dir = prep_tree_for_archive(clone_dir, args.subdir, args.outdir,
                                    dstname=dstname)
    CLEANUP_DIRS.append(tar_dir)

    archive = TarSCM.archive()

    archive.extract_from_archive(tar_dir, args.extract, args.outdir)

    # FIXME: Consolidate calling parameters and shrink to one call of create_archive
    if use_obs_scm:
        tmp_archive = TarSCM.archive.obscpio()
        tmp_archive.create_archive(
                scm_object,
                tar_dir,
                basename,
                dstname,
                version,
                scm_object.get_current_commit(clone_dir),
                args)
    else:
        tmp_archive = TarSCM.archive.tar()
        tmp_archive.create_archive(
                scm_object,
                tar_dir,
                args.outdir,
                dstname=dstname,
                extension=args.extension,
                exclude=args.exclude,
                include=args.include,
                package_metadata=args.package_meta,
                timestamp=get_timestamp(scm_object, args, clone_dir))

    if changes:
        changesauthor = get_changesauthor(args)

        logging.debug("AUTHOR: %s", changesauthor)

        if not version:
            args.version = "_auto_"
            changesversion = get_version(scm_object, args, clone_dir)

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
