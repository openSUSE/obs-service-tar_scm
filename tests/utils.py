#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Simple utility functions to help executing processes.
from typing import Any, Iterable, Optional, Tuple

import os
import re
import io
import shutil
import subprocess
import sys


def mkfreshdir(path: str) -> None:
    if not re.search('.{10}/tmp(/|$)', path):
        raise RuntimeError('unsafe call: mkfreshdir(%s)' % path)

    cwd = os.getcwd()
    os.chdir('/')
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)
    os.chdir(cwd)


def check_locale(loc: Iterable[str]) -> str:
    aloc_tmp = subprocess.check_output(['locale', '-a'])
    aloc = {}

    for available_loc in aloc_tmp.split(b'\n'):
        aloc[available_loc] = 1

    for requested_loc in loc:
        print("Checking .... %s" % requested_loc, file=sys.stderr)
        try:
            if aloc[requested_loc.encode()]:
                return requested_loc
        except KeyError:
            pass

    return 'C'

def run_cmd(cmd: str) -> Tuple[bytes, bytes, int]:
    use_locale = check_locale(["en_US.utf8", 'C.utf8'])
    os.environ['LANG']   = use_locale
    os.environ['LC_ALL'] = use_locale
    proc = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)

    (stdout, stderr) = proc.communicate()
    return (stdout, stderr, proc.returncode)


def quietrun(cmd: str) -> Tuple[bytes, bytes, int]:
    (stdout, stderr, ret) = run_cmd(cmd)
    if ret != 0:
        print(cmd, " failed!")
        print(stdout)
        print(stderr)
    return (stdout, stderr, ret)


def run_scm(scm: str, repo: Optional[str], args: str) -> Tuple[bytes, bytes, int]:
    cmd = '%s %s' % (scm, args)
    if repo:
        cmd = 'cd %s && %s' % (repo, cmd)
    # return subprocess.check_output(cmd, shell=True)
    return quietrun(cmd)


def run_git(args: str) -> Tuple[bytes, bytes, int]:
    return run_scm('git', None, args)


def run_svn(repo: str, args: str) -> Tuple[bytes, bytes, int]:
    return run_scm('svn', repo, args)


def run_hg(repo: str, args: str) -> Tuple[bytes, bytes, int]:
    return run_scm('hg',  repo, args)


def run_bzr(repo: str, args: str) -> Tuple[bytes, bytes, int]:
    return run_scm('bzr', repo, args)


def file_write_legacy(fname: str, in_str: object, mode: str = 'w') -> None:
    '''Write string data to a file.'''
    with io.open(fname, mode, encoding='utf-8') as outfile:
        outfile.write(str(in_str))
