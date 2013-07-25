# tar_scm (OBS source service) [![Build Status](https://travis-ci.org/openSUSE/obs-service-tar_scm.png?branch=master)](https://travis-ci.org/openSUSE/obs-service-tar_scm)

This is the git repository for openSUSE:Tools/obs-service-tar_scm.
The authoritative source is:

    https://github.com/openSUSE/obs-service-tar_scm

The files in this top-level directory are installed at the following
locations:

    tar_scm.config  -> /etc/obs/services/tar_scm
    tar_scm         -> /usr/lib/obs/service/tar_scm
    tar_scm.service -> /usr/lib/obs/service/tar_scm.service

Run the test suite via:

    python tests/test.py

N.B. pull requests are very welcome, but will not be accepted unless
they contain corresponding additions/modifications to the test suite.
Thanks in advance!
