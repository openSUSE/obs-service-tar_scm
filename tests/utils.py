#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Simple utility functions to help executing processes.
from __future__ import print_function

import os
import re
import io
import shutil
import subprocess
import sys
import six


def mkfreshdir(path):
    if not re.search('.{10}/tmp(/|$)', path):
        raise RuntimeError('unsafe call: mkfreshdir(%s)' % path)

    cwd = os.getcwd()
    os.chdir('/')
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)
    os.chdir(cwd)

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
        print("Checking .... %s"%tloc, file=sys.stderr)
        try:
            if aloc[tloc.encode()]:
                return tloc
        except KeyError:
            pass

    return 'C'

def run_cmd(cmd):
    use_locale = check_locale(["en_US.utf8", 'C.utf8'])
    os.environ['LANG']   = use_locale
    os.environ['LC_ALL'] = use_locale
    if six.PY3:
        cmd = cmd.encode('UTF-8')
    proc = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)

    (stdout, stderr) = proc.communicate()
    return (stdout, stderr, proc.returncode)


def quietrun(cmd):
    (stdout, stderr, ret) = run_cmd(cmd)
    if ret != 0:
        print(cmd, " failed!")
        print(stdout)
        print(stderr)
    return (stdout, stderr, ret)


def run_scm(scm, repo, args):
    cmd = '%s %s' % (scm, args)
    if repo:
        cmd = 'cd %s && %s' % (repo, cmd)
    # return subprocess.check_output(cmd, shell=True)
    return quietrun(cmd)


def run_git(args):
    return run_scm('git', None, args)


def run_svn(repo, args):
    return run_scm('svn', repo, args)


def run_hg(repo, args):
    return run_scm('hg',  repo, args)


def file_write_legacy(fname, string, *args):
    '''function to write string to file python 2/3 compatible'''
    mode = 'w'
    if args:
        mode = args[0]

    with io.open(fname, mode, encoding='utf-8') as outfile:
        # 'str().encode().decode()' is required for pyhton 2/3 compatibility
        outfile.write(str(string).encode('UTF-8').decode('UTF-8'))
