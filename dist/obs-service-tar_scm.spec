#
# spec file for package obs-service-tar_scm
#
# Copyright (c) 2019 SUSE LINUX GmbH, Nuernberg, Germany.
#
# All modifications and additions to the file contributed by third parties
# remain the property of their copyright owners, unless otherwise agreed
# upon. The license for this file, and modifications and additions to the
# file, is the same license as for the pristine package itself (unless the
# license for the pristine package is not an Open Source License, in which
# case the license is the MIT License). An "Open Source License" is a
# license that conforms to the Open Source Definition (Version 1.9)
# published by the Open Source Initiative.

# Please submit bugfixes or comments via https://bugs.opensuse.org/
#


%if 0%{?suse_version}
%if 0%{?suse_version} >= 1550 || 0%{?sle_version} >= 150100
%define locale_package glibc-locale-base
%else
%define locale_package glibc-locale
%endif
%endif

%if 0%{?fedora_version} >= 24 || 0%{?rhel_version} >= 800 || 0%{?centos_version} >= 800
%define locale_package glibc-langpack-en
%else
%define locale_package glibc-common
%endif
%endif

%if 0%{?mageia} || 0%{?mandriva_version}
%define locale_package locales
%endif

# avoid code duplication
%define scm_common_dep                                          \
Requires:       obs-service-obs_scm-common = %version-%release  \
%{nil}

%define scm_dependencies                                        \
Requires:       git-core                                        \
%if 0%{?suse_version} >= 1315                                   \
Recommends:     mercurial                                       \
Recommends:     subversion                                      \
Recommends:     obs-service-download_files                      \
%endif                                                          \
%{nil}

######## END OF MACROS AND FUN ###################################

Name:           obs-service-tar_scm
%define version_unconverted 0.10.9.1557261720.32a1cdb
Version:        0.10.9.1557261720.32a1cdb
Release:        0
Summary:        An OBS source service: create tar ball from svn/git/hg
License:        GPL-2.0-or-later
Group:          Development/Tools/Building
Url:            https://github.com/openSUSE/obs-service-tar_scm
Source:         %{name}-%{version}.tar.gz

# Fix build on Ubuntu by disabling mercurial tests, not applied in rpm
# based distributions
#Patch0:         0001-Debianization-disable-running-mercurial-tests.patch

BuildRequires:  %{locale_package}
BuildRequires:  python3-six
BuildRequires:  python3-unittest2
BuildRequires:  git-core
BuildRequires:  mercurial
BuildRequires:  subversion

BuildRequires:  %{locale_package}
BuildRequires:  python3-PyYAML
BuildRequires:  python3-dateutil
BuildRequires:  python3-keyring
BuildRequires:  python3-keyrings.alt
# Why do we need this? we dont use it as runtime requires later
BuildRequires:  python3-lxml

BuildRequires:  python3
%scm_common_dep
%scm_dependencies
#
#
#
BuildRoot:      %{_tmppath}/%{name}-%{version}-build
BuildArch:      noarch

%description
This is a source service for openSUSE Build Service.

It supports downloading from svn, git, hg repositories.

%package -n     obs-service-obs_scm-common
Summary:        Common parts of SCM handling services
Group:          Development/Tools/Building
Requires:       %{locale_package}
Requires:       python3-PyYAML
Requires:       python3-dateutil

%description -n obs-service-obs_scm-common
This is a source service for openSUSE Build Service.

It supports downloading from svn, git, hg repositories.

This package holds the shared files for different services.

%package -n     obs-service-tar
Summary:        Creates a tar archive from local directory
Group:          Development/Tools/Building
Provides:       obs-service-tar_scm:/usr/lib/obs/service/tar.service
%scm_common_dep

%description -n obs-service-tar
Creates a tar archive from local directory

%package -n     obs-service-obs_scm
Summary:        Creates a OBS cpio from a remote SCM resource
Group:          Development/Tools/Building
Provides:       obs-service-tar_scm:/usr/lib/obs/service/obs_scm.service
%scm_common_dep
%scm_dependencies

%description -n obs-service-obs_scm
Creates a OBS cpio from a remote SCM resource.

This can be used to work directly in local git checkout and can be packaged
into a tar ball during build time.

%package -n     obs-service-appimage
Summary:        Handles source downloads defined in appimage.yml files
Group:          Development/Tools/Building
%scm_common_dep
%scm_dependencies

%description -n obs-service-appimage
Experimental appimage support: This parses appimage.yml files for SCM
resources and packages them.

%package -n     obs-service-snapcraft
Summary:        Handles source downloads defined in snapcraft.yaml files
Group:          Development/Tools/Building
Provides:       obs-service-tar_scm:/usr/lib/obs/service/snapcraft.service
%scm_common_dep
%scm_dependencies

%description -n obs-service-snapcraft
Experimental snapcraft support: This parses snapcraft.yaml files for SCM
resources and packages them.

%package -n     obs-service-gbp
Summary:        Creates Debian source artefacts from a Git repository
Group:          Development/Tools/Building
Requires:       git-buildpackage >= 0.6.0
Requires:       obs-service-obs_scm-common = %version-%release
Provides:       obs-service-tar_scm:/usr/lib/obs/service/obs_gbp.service

%description -n obs-service-gbp
Debian git-buildpackage workflow support: uses gbp to create Debian
source artefacts (.dsc, .origin.tar.gz and .debian.tar.gz if non-native).

%prep
%setup -q -n obs-service-tar_scm-%version

%build

%install
make install DESTDIR="%{buildroot}" PREFIX="%{_prefix}" SYSCFG="%{_sysconfdir}" PYTHON="%{_bindir}/python3"

%check
# No need to run PEP8 tests here; that would require a potentially
# brittle BuildRequires: python-pycodestyle, and any style issues are already
# caught by Travis CI.
make test

%files
%{_prefix}/lib/obs/service/tar_scm.service

%files -n obs-service-obs_scm-common
%dir %{_prefix}/lib/obs
%dir %{_prefix}/lib/obs/service
%{_prefix}/lib/obs/service/TarSCM
%{_prefix}/lib/obs/service/tar_scm
%dir %{_sysconfdir}/obs
%dir %{_sysconfdir}/obs/services
%attr(-,obsservicerun,obsrun) %dir %{_sysconfdir}/obs/services/tar_scm.d
%config(noreplace) %{_sysconfdir}/obs/services/*

%files -n obs-service-tar
%{_prefix}/lib/obs/service/tar
%{_prefix}/lib/obs/service/tar.service

%files -n obs-service-obs_scm
%{_prefix}/lib/obs/service/obs_scm
%{_prefix}/lib/obs/service/obs_scm.service

%files -n obs-service-appimage
%{_prefix}/lib/obs/service/appimage*

%files -n obs-service-snapcraft
%{_prefix}/lib/obs/service/snapcraft*

%files -n obs-service-gbp
%{_prefix}/lib/obs/service/obs_gbp*

%changelog
