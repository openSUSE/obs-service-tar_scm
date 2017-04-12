#!/usr/bin/env python2

import os
from pprint import pprint, pformat
import re
import sys
import tarfile

if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

line_start = '(^|\n)'


class TestAssertions(unittest.TestCase):

    """Library of test assertions used by tar_scm unit tests.

    This class augments Python's standard unittest.TestCase assertions
    with operations which the tar_scm unit tests commonly need.
    """

    ######################################################################
    # backported from 2.7 just in case we're running on an older Python
    def assertRegexpMatches(self, text, expected_regexp, msg=None):
        """Fail the test unless the text matches the regular expression."""
        if isinstance(expected_regexp, basestring):
            expected_regexp = re.compile(expected_regexp)
        if not expected_regexp.search(text):
            msg = msg or "Regexp didn't match"
            msg = '%s: %r not found in %r' % \
                  (msg, expected_regexp.pattern, text)
            raise self.failureException(msg)

    def assertNotRegexpMatches(self, text, unexpected_regexp, msg=None):
        """Fail the test if the text matches the regular expression."""
        if isinstance(unexpected_regexp, basestring):
            unexpected_regexp = re.compile(unexpected_regexp)
        match = unexpected_regexp.search(text)
        if match:
            msg = msg or "Regexp matched"
            msg = '%s: %r matches %r in %r' % (msg,
                                               text[match.start():match.end()],
                                               unexpected_regexp.pattern,
                                               text)
            raise self.failureException(msg)
    ######################################################################

    def assertNumDirents(self, dir, expected, msg=''):
        dirents = os.listdir(dir)
        got = len(dirents)
        if len(msg) > 0:
            msg += "\n"
        msg += 'expected %d file(s), got %d: %s' % \
               (expected, got, pformat(dirents))
        self.assertEqual(expected, got, msg)
        return dirents

    def assertNumTarEnts(self, tar, expected, msg=''):
        self.assertTrue(tarfile.is_tarfile(tar))
        th = tarfile.open(tar)
        tarents = th.getmembers()
        got = len(tarents)
        if len(msg) > 0:
            msg += "\n"
        msg += 'expected %s to have %d entries, got %d:\n%s' % \
            (tar, expected, got, pformat(tarents))
        self.assertEqual(expected, got, msg)
        return th, tarents

    def assertDirentsMtime(self, entries):
        '''This test is disabled on Python 2.6 because tarfile is not able to
        directly change the mtime for an entry in the tarball.'''
        if sys.hexversion < 0x02070000:
            return
        for i in range(0, len(entries)):
            self.assertEqual(entries[i].mtime, 1234567890)

    def assertDirents(self, entries, top):
        self.assertEqual(entries[0].name, top)
        self.assertEqual(entries[1].name, top + '/a')
        self.assertEqual(entries[2].name, top + '/c')
        self.assertDirentsMtime(entries)

    def assertSubdirDirents(self, entries, top):
        self.assertEqual(entries[0].name, top)
        self.assertEqual(entries[1].name, top + '/b')
        self.assertDirentsMtime(entries)

    def assertStandardTar(self, tar, top):
        th, entries = self.assertNumTarEnts(tar, 5)
        entries.sort(lambda x, y: cmp(x.name, y.name))
        self.assertDirents(entries[:3], top)
        self.assertSubdirDirents(entries[3:], top + '/subdir')
        return th

    def assertSubdirTar(self, tar, top):
        th, entries = self.assertNumTarEnts(tar, 2)
        entries.sort(lambda x, y: cmp(x.name, y.name))
        self.assertSubdirDirents(entries, top)
        return th

    def assertIncludeSubdirTar(self, tar, top):
        th, entries = self.assertNumTarEnts(tar, 3)
        entries.sort(lambda x, y: cmp(x.name, y.name))
        self.assertEqual(entries[0].name, top)
        self.assertSubdirDirents(entries[1:], top + '/subdir')
        return th

    def checkTar(self, tar, tarbasename, toptardir=None, tarchecker=None):
        if not toptardir:
            toptardir = tarbasename
        if not tarchecker:
            tarchecker = self.assertStandardTar

        self.assertEqual(tar, '%s.tar' % tarbasename)
        tarpath = os.path.join(self.outdir, tar)
        return tarchecker(tarpath, toptardir)

    def assertTarOnly(self, tarbasename, **kwargs):
        dirents = self.assertNumDirents(self.outdir, 1)
        return self.checkTar(dirents[0], tarbasename, **kwargs)

    def assertTarAndDir(self, tarbasename, dirname=None, **kwargs):
        if not dirname:
            dirname = tarbasename

        dirents = self.assertNumDirents(self.outdir, 2)
        pprint(dirents)

        if dirents[0][-4:] == '.tar':
            tar = dirents[0]
            wd  = dirents[1]
        elif dirents[1][-4:] == '.tar':
            tar = dirents[1]
            wd  = dirents[0]
        else:
            self.fail('no .tar found in ' + self.outdir)

        self.assertEqual(wd, dirname)
        self.assertTrue(os.path.isdir(os.path.join(self.outdir, wd)),
                        dirname + ' should be directory')

        return self.checkTar(tar, tarbasename, **kwargs)

    def assertTarMemberContains(self, th, tarmember, contents):
        f = th.extractfile(tarmember)
        self.assertEqual(contents, "\n".join(f.readlines()))

    def assertRanInitialClone(self, logpath, loglines):
        self._find(logpath, loglines,
                   self.initial_clone_command, self.update_cache_command)

    def assertSSLVerifyFalse(self, logpath, loglines):
        self._find(logpath, loglines,
                   self.initial_clone_command +
                   '.*' + self.sslverify_false_args,
                   self.sslverify_false_args + 'true')

    def assertRanUpdate(self, logpath, loglines):
        self._find(logpath, loglines,
                   self.update_cache_command, self.initial_clone_command)

    def _find(self, logpath, loglines, should_find, should_not_find):
        found = False
        regexp = re.compile('^' + should_find)
        for line in loglines:
            msg = \
                "Shouldn't find /%s/ in %s; log was:\n" \
                "----\n%s\n----\n" \
                % (should_not_find, logpath, "".join(loglines))
            self.assertNotRegexpMatches(line, should_not_find, msg)
            if regexp.search(line):
                found = True
        msg = \
            "Didn't find /%s/ in %s; log was:\n" \
            "----\n%s\n----\n" \
            % (regexp.pattern, logpath, "".join(loglines))
        self.assertTrue(found, msg)
