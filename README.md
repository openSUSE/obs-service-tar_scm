# tar_scm (OBS source service) [![Build Status](https://travis-ci.org/openSUSE/obs-service-tar_scm.png?branch=master)](https://travis-ci.org/openSUSE/obs-service-tar_scm)

This is an [Open Build Service](http://openbuildservice.org/) source service. It uses an SCM client to checkout or update a package by creating a source tarball from a source code repository.

It supports many options, e.g. it can adjust resulting tarball parameters, include or exclude particular files when creating this tarball or generate an rpm changelog from the SCM commit log. For the full list of options please see tar_scm.service.in.

Apart from various SCM like git, hg, bzr or svn it additionally supports `--url` option that allows you to specify URL of the upstream tarball to be downloaded.

This is the git repository for [openSUSE:Tools/obs-service-tar_scm](https://build.opensuse.org/package/show/openSUSE:Tools/obs-service-tar_scm). The authoritative source is https://github.com/openSUSE/obs-service-tar_scm

The service can be used in combination with other services like [download_files](https://github.com/openSUSE/obs-service-download_files), [extract_file](https://github.com/openSUSE/obs-service-extract_file), [recompress](https://github.com/openSUSE/obs-service-recompress) or [set_version](https://github.com/openSUSE/obs-service-set_version) e.g. within the [GIT integration](https://en.opensuse.org/openSUSE:Build_Service_Concept_SourceService#Example_2:_GIT_integration) workflow.

## Installation
The files in this top-level directory need to be installed using the following:

    make install

## Test suite

See the [TESTING.md](TESTING.md) file.

## Contributions

See the [CONTRIBUTING.md](CONTRIBUTING.md) file.
