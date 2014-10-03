#!/usr/bin/python
#
# Simple utility functions to help executing processes.

import os
import re
import shutil
import subprocess


def mkfreshdir(path):
    if not re.search('.{10}/tmp(/|$)', path):
        raise RuntimeError('unsafe call: mkfreshdir(%s)' % path)

    cwd = os.getcwd()
    os.chdir('/')
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)
    os.chdir(cwd)


def run_cmd(cmd):
    p = subprocess.Popen(cmd, shell=True,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    (stdout, stderr) = p.communicate()
    return (stdout, stderr, p.returncode)


def quietrun(cmd):
    (stdout, stderr, ret) = run_cmd(cmd)
    if ret != 0:
        print cmd, " failed!"
        print stdout
        print stderr
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


def run_bzr(repo, args):
    return run_scm('bzr', repo, args)
