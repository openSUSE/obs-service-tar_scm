#
# spec file for package obs-service-tar_scm
#
# Copyright (c) 2018 SUSE LINUX GmbH, Nuernberg, Germany.
#
# All modifications and additions to the file contributed by third parties
# remain the property of their copyright owners, unless otherwise agreed
# upon. The license for this file, and modifications and additions to the
# file, is the same license as for the pristine package itself (unless the
# license for the pristine package is not an Open Source License, in which
# case the license is the MIT License). An "Open Source License" is a
# license that conforms to the Open Source Definition (Version 1.9)
# published by the Open Source Initiative.

# Please submit bugfixes or comments via http://bugs.opensuse.org/
#


%bcond_without obs_scm_testsuite

Name:           obs-service-tar_scm
%define version_unconverted 0.8.0.1520581079.e26b0ae
Version:        0.8.0.1520581079.e26b0ae
Release:        0
Summary:        An OBS source service: create tar ball from svn/git/hg
License:        GPL-2.0-or-later
Group:          Development/Tools/Building
Url:            https://github.com/openSUSE/obs-service-tar_scm
Source:         %{name}-%{version}.tar.gz
# Fix build on Ubuntu by disabling mercurial tests, not applied in rpm
# based distributions
#Patch0:         0001-Debianization-disable-running-mercurial-tests.patch
%if %{with obs_scm_testsuite}
BuildRequires:  bzr
BuildRequires:  git-core
BuildRequires:  mercurial
BuildRequires:  subversion
%if 0%{?fedora_version} || 0%{?rhel_version} || 0%{?centos_version}
%define py_compile(O)  \
find %1 -name '*.pyc' -exec rm -f {} \\; \
python -c "import sys, os, compileall; br='%{buildroot}'; compileall.compile_dir(sys.argv[1], ddir=br and (sys.argv[1][len(os.path.abspath(br)):]+'/') or None)" %1 \
%{-O: \
find %1 -name '*.pyo' -exec rm -f {} \\; \
python -O -c "import sys, os, compileall; br='%{buildroot}'; compileall.compile_dir(sys.argv[1], ddir=br and (sys.argv[1][len(os.path.abspath(br)):]+'/') or None)" %1 \
}

BuildRequires:  PyYAML
%else
BuildRequires:  python-PyYAML
%endif
BuildRequires:  python-dateutil
BuildRequires:  python-lxml
BuildRequires:  python-mock
BuildRequires:  python-unittest2
%endif
BuildRequires:  python >= 2.6
Requires:       git-core
Recommends:     bzr
Recommends:     mercurial
Recommends:     subversion
Requires:       obs-service-obs_scm-common = %version-%release
BuildRoot:      %{_tmppath}/%{name}-%{version}-build
BuildArch:      noarch

%description
This is a source service for openSUSE Build Service.

It supports downloading from svn, git, hg and bzr repositories.

%package -n     obs-service-obs_scm-common
Summary:        Common parts of SCM handling services
Group:          Development/Tools/Building
Requires:       python-dateutil
%if 0%{?fedora_version} || 0%{?rhel_version} || 0%{?centos_version}
Requires:       PyYAML
%else
Requires:       python-PyYAML
%if 0%{?suse_version} < 1315
Requires:       python-argparse
%endif
%endif

%if 0%{?fedora_version} >= 25
Requires:       python2
%endif

%description -n obs-service-obs_scm-common

%package -n     obs-service-tar
Summary:        Creates a tar archive from local directory
Group:          Development/Tools/Building
Requires:       obs-service-obs_scm-common = %version-%release
Provides:       obs-service-tar_scm:/usr/lib/obs/service/tar.service

%description -n obs-service-tar
Creates a tar archive from local directory

%package -n     obs-service-obs_scm
Summary:        Creates a OBS cpio from a remote SCM resource
Group:          Development/Tools/Building
Provides:       obs-service-tar_scm:/usr/lib/obs/service/obs_scm.service
Requires:       git-core
Recommends:     bzr
Recommends:     mercurial
Recommends:     subversion
Requires:       obs-service-obs_scm-common = %version-%release

%description -n obs-service-obs_scm
Creates a OBS cpio from a remote SCM resource.

This can be used to work directly in local git checkout and can be packaged
into a tar ball during build time.

%package -n     obs-service-appimage
Summary:        Handles source downloads defined in appimage.yml files
Group:          Development/Tools/Building
Requires:       git-core
Recommends:     bzr
Recommends:     mercurial
Recommends:     subversion
Requires:       obs-service-obs_scm-common = %version-%release

%description -n obs-service-appimage
Experimental appimage support: This parses appimage.yml files for SCM
resources and packages them.

%package -n     obs-service-snapcraft
Summary:        Handles source downloads defined in snapcraft.yaml files
Group:          Development/Tools/Building
Provides:       obs-service-tar_scm:/usr/lib/obs/service/snapcraft.service
Requires:       git-core
Recommends:     bzr
Recommends:     mercurial
Recommends:     subversion
Requires:       obs-service-obs_scm-common = %version-%release

%description -n obs-service-snapcraft
Experimental snapcraft support: This parses snapcraft.yaml files for SCM
resources and packages them.


%prep
%setup -q -n obs-service-tar_scm-%version

%build
%if 0%{?fedora_version} || 0%{?rhel_version} || 0%{?centos_version}
%py_compile .
%else
%py_compile %{buildroot}
%endif

%install
make install DESTDIR="%{buildroot}" PREFIX="%{_prefix}" SYSCFG="%{_sysconfdir}"

%if %{with obs_scm_testsuite}
%if 0%{?suse_version} >= 1220

%check
# No need to run PEP8 tests here; that would require a potentially
# brittle BuildRequires: python-pep8, and any style issues are already
# caught by Travis CI.
make test
%endif
%endif

%files
%defattr(-,root,root)
%{_prefix}/lib/obs/service/tar_scm.service

%files -n obs-service-obs_scm-common
%defattr(-,root,root)
%dir %{_prefix}/lib/obs
%dir %{_prefix}/lib/obs/service
%{_prefix}/lib/obs/service/TarSCM
%{_prefix}/lib/obs/service/tar_scm
%dir %{_sysconfdir}/obs
%dir %{_sysconfdir}/obs/services
%config(noreplace) %{_sysconfdir}/obs/services/*

%files -n obs-service-tar
%defattr(-,root,root)
%{_prefix}/lib/obs/service/tar
%{_prefix}/lib/obs/service/tar.service

%files -n obs-service-obs_scm
%defattr(-,root,root)
%{_prefix}/lib/obs/service/obs_scm
%{_prefix}/lib/obs/service/obs_scm.service

%files -n obs-service-appimage
%defattr(-,root,root)
%{_prefix}/lib/obs/service/appimage*

%files -n obs-service-snapcraft
%defattr(-,root,root)
%{_prefix}/lib/obs/service/snapcraft*

%changelog
