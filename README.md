# tar_scm (OBS source service) [![Build Status](https://travis-ci.org/openSUSE/obs-service-tar_scm.png?branch=master)](https://travis-ci.org/openSUSE/obs-service-tar_scm)

This is the git repository for
[openSUSE:Tools/obs-service-tar_scm](https://build.opensuse.org/package/show/openSUSE:Tools/obs-service-tar_scm),
which provides several [source
services](http://openbuildservice.org/help/manuals/obs-user-guide/cha.obs.source_service.html)
for the [Open Build Service](http://openbuildservice.org/) which all
assist with packaging source code from SCM (source code management)
repositories into tarballs.  The authoritative source is
https://github.com/openSUSE/obs-service-tar_scm.

## Services

### tar_scm *(deprecated)*

`tar_scm` is the legacy source service used to create a source tarball
from one of the supported SCM (source code management) tools: `git`,
`hg`, `svn`, and `bzr`.

`tar_scm` supports many options, e.g. it can adjust resulting tarball
parameters, include or exclude particular files when creating the
tarball, or generate an `rpm` changelog from the SCM commit log. For the
full list of options please see `tar_scm.service.in`.

Apart from various SCM like git, hg, bzr or svn, it additionally
supports `--url` option that allows you to specify URL of the upstream
tarball to be downloaded.

`tar_scm` can be used in combination with other services like
[download_files](https://github.com/openSUSE/obs-service-download_files),
[recompress](https://github.com/openSUSE/obs-service-recompress) or
[set_version](https://github.com/openSUSE/obs-service-set_version)
e.g. within the [GIT integration](https://en.opensuse.org/openSUSE:Build_Service_Concept_SourceService#Example_2:_GIT_integration)
workflow.

**`tar_scm` is deprecated in favour of `obs_scm`.**

### obs_scm

`obs_scm` is similar in concept to `tar_scm`, but instead of directly
generating tarballs, it instead uses the new `obscpio` archive format
(see below) as an intermediate space-efficient format in which to
store the sources.

**It is recommended to use `obs_scm` in favour to `tar_scm`**, because
it provides the following advantages:

1. When you `osc checkout`, you'll also get a local checkout directory
   within the project directory, inside which you can develop as usual
   and test your changes with local builds, even without having to
   commit or push your changes anywhere.

2. It helps to save a *lot* of disk space on the server side,
   especially when used in continuous integration (e.g. nightly builds
   and builds of pull requests).

The usual source tarballs can be regenerated from this at build-time
using the `tar` and `recompress` source services, so no changes to
`.spec` files are required when switching to `obs_scm` and `obscpio`.

Having said that, it may be more efficient to drop the build-time
usage of `recompress`, since at build-time `rpmbuild` would decompress
the same file soon after compressing it.  In this case, only the `tar`
source service would be used to reconstruct an uncompressed tarball to
be consumed by the `.spec` file.  However this has the side-effect
that the resulting `.src.rpm` will contain an uncompressed tarball
too.  This is not necessarily a problem because `.src.rpm` files are
compressed anyway, and in fact it may even be *more* efficient to
avoid double compression (i.e. the sources within the `.src.rpm`, and
the `.src.rpm` itself both being compressed).  But this depends very
much on the combination of compression formats used for compression of
the sources, and for compression of the `.src.rpm`.  Therefore the
decision whether to use `recompress` will depend on what format is
desired within the resulting `.src.rpm`, and on the types of
compression being used for both the tarball and by `rpmbuild` for
constructing the source rpms.

`obs_scm` additionally generates a file named `<package>.obsinfo`
which includes useful information from your SCM system, such as the
name, version number, mtime, and commit SHA1.  This data is then used
by the `tar` service (see below) to reconstruct a tarball for use by
`rpmbuild` at build-time, and also by the
[`set_version`](https://github.com/openSUSE/obs-service-set_version)
source service in order to set the version in build description files
such as `.spec` or `.dsc` files.

### tar

The `tar` source service creates a tarball out of a `.obscpio` archive
and a corresponding `.obsinfo` file which contains metadata about it.
Typically this service is run at build-time, e.g.

    <service name="tar" mode="buildtime"/>

since storing the `.tar` file in OBS would duplicate the source data
in the `.obscpio` and defeat the point of using `.obscpio` in the
first place, which is to save space on the OBS server.

See http://openbuildservice.org/2016/04/08/new_git_in_27/ for an example
combining usage of the `obs_scm` and `tar` source services.

### snapcraft

The `snapcraft` source service can be used to fetch sources before
building a [`snappy` app (a.k.a. *snap*)](https://snapcraft.io/).

It parses [a `snapcraft.yaml`
file](https://docs.snapcraft.io/build-snaps/syntax), looking for any
[parts in the `parts`
section](https://docs.snapcraft.io/build-snaps/parts) which have
[`source-type`](https://docs.snapcraft.io/reference/plugins/source)
set to one of the supported SCMs.  For each one it will fetch the
sources via the SCM from the upstream repository, and build a tarball
from it.

Finally it will write a new version of `snapcraft.yaml` which has the
`source` value rewritten from the original URL, to the name of the
part, which is also the name of the newly created local file.  This
allows the snap to be built purely from local files.

### appimage

The `appimage` source service can be used to fetch sources before
building an [AppImage](http://appimage.org/).  It parses [an
`appimage.yml`
file](https://github.com/AppImage/AppImages/blob/master/YML.md), looks
for an optional `build` section at the top-level, and for any sub-key
named after a supported SCM, it will treat the corresponding value as
a URL, fetch the sources via the SCM from the upstream repository, and
build a tarball from it.  You can find example `appimage.yml` files
under the `tests/fixtures/` subdirectory.

## Archive Formats

### tar

The standard `tar` archive format is used as output format by the
`tar` and `tar_scm` source services.

### obscpio

`obscpio` archives are
[`cpio`](https://www.gnu.org/software/cpio/manual/cpio.html) archives
in `newc` format.  Using these allows the [OBS Delta
Store](http://openbuildservice.org/help/manuals/obs-reference-guide/cha.obs.architecture.html#delta_store)
to store changes server-side in a space-efficient incremental way,
independently of your chosen SCM.  Then at build-time, the `tar`
source service converts a file from this format into a regular `.tar`
for use by `rpmbuild`.  This is described in more detail in this blog
post:

- http://openbuildservice.org/2016/04/08/new_git_in_27/

## Installation

The files in this top-level directory need to be installed using the
following:

    make install

## User documentation

There isn't yet any comprehensive user documentation (see [issue
#238](https://github.com/openSUSE/obs-service-tar_scm/issues/238)),
but in the meantime, in addition to the information in this README,
the following resources may be helpful:

- The XML `.service` files which document the parameters for
  each source service:
  - the [`tar_scm.service.in` template](https://github.com/openSUSE/obs-service-tar_scm/blob/master/tar_scm.service.in)
    which is used to generate `tar_scm.service` and `obs_scm.service`
  - [`appimage.service`](https://github.com/openSUSE/obs-service-tar_scm/blob/master/appimage.service)
  - [`snapcraft.service`](https://github.com/openSUSE/obs-service-tar_scm/blob/master/snapcraft.service)
  - [`tar.service`](https://github.com/openSUSE/obs-service-tar_scm/blob/master/tar.service)
- The ["Using Source Services" chapter](https://openbuildservice.org/help/manuals/obs-user-guide/cha.obs.source_service.html)
  of [the OBS User Guide](https://openbuildservice.org/help/manuals/obs-user-guide/)

## Test suite

See the [TESTING.md](TESTING.md) file.

## Contributions

See the [CONTRIBUTING.md](CONTRIBUTING.md) file.
