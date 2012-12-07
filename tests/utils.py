#!/usr/bin/python

import os
import re
import shutil
import subprocess

def mkfreshdir(path):
    if not re.search('.{10}/tmp(/|$)', path):
        raise RuntimeError, 'unsafe call: mkfreshdir(%s)' % path

    cwd = os.getcwd()
    os.chdir('/')
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)

def run_cmd(cmd):
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (stdout, stderr) = p.communicate()
    return (stdout, stderr, p.returncode)

def quietrun(cmd):
    (stdout, stderr, ret) = run_cmd(cmd)
    if ret != 0:
        print cmd, " failed!"
        print stdout
        print stderr
    return (stdout, stderr, ret)

def run_scm(scm, repo, opts):
    cmd = 'cd %s && %s %s' % (repo, scm, opts)
    #return subprocess.check_output(cmd, shell=True)
    return quietrun(cmd)

def run_git(repo, opts):
    return run_scm('git', repo, opts)

def run_svn(repo, opts):
    return run_scm('svn', repo, opts)

def run_hg(repo, opts):
    return run_scm('hg',  repo, opts)

def run_bzr(repo, opts):
    return run_scm('bzr', repo, opts)
