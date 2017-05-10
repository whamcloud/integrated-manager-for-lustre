%global with_debug 1

%{?!_pkgdocdir:%global _pkgdocdir %{_docdir}/%{name}-%{version}}

# ARM builds currently break on the Debug builds, so we'll just
# build the standard runtime until that gets sorted out.
%ifarch %{arm} aarch64 %{power64}
%global with_debug 0
%endif

# == Node.js Version ==
# Note: Fedora should only ship LTS versions of Node.js (currently expected
# to be major versions with even numbers). The odd-numbered versions are new
# feature releases that are only supported for nine months, which is shorter
# than a Fedora release lifecycle.
%global nodejs_epoch 1
%global nodejs_major 6
%global nodejs_minor 10
%global nodejs_patch 1
%global nodejs_abi %{nodejs_major}.%{nodejs_minor}
%global nodejs_version %{nodejs_major}.%{nodejs_minor}.%{nodejs_patch}
%global nodejs_release 2.04

# == Bundled Dependency Versions ==
# v8 - from deps/v8/include/v8-version.h
%global v8_major 5
%global v8_minor 1
%global v8_build 281
%global v8_patch 95
# V8 presently breaks ABI at least every x.y release while never bumping SONAME
%global v8_abi %{v8_major}.%{v8_minor}
%global v8_version %{v8_major}.%{v8_minor}.%{v8_build}.%{v8_patch}

# c-ares - from deps/cares/include/ares_version.h
%global c_ares_major 1
%global c_ares_minor 10
%global c_ares_patch 1
%global c_ares_version %{c_ares_major}.%{c_ares_minor}.%{c_ares_patch}

# http-parser - from deps/http_parser/http_parser.h
%global http_parser_major 2
%global http_parser_minor 7
%global http_parser_patch 0
%global http_parser_version %{http_parser_major}.%{http_parser_minor}.%{http_parser_patch}

# punycode - from lib/punycode.js
# Note: this was merged into the mainline since 0.6.x
# Note: this will be unmerged in v7 or v8
%global punycode_major 2
%global punycode_minor 0
%global punycode_patch 0
%global punycode_version %{punycode_major}.%{punycode_minor}.%{punycode_patch}

# npm - from deps/npm/package.json
%global npm_epoch 1
%global npm_major 3
%global npm_minor 10
%global npm_patch 10
%global npm_version %{npm_major}.%{npm_minor}.%{npm_patch}

# In order to avoid needing to keep incrementing the release version for the
# main package forever, we will just construct one for npm that is guaranteed
# to increment safely. Changing this can only be done during an update when the
# base npm version number is increasing.
%global npm_release %{nodejs_epoch}.%{nodejs_major}.%{nodejs_minor}.%{nodejs_patch}.%{nodejs_release}

# Filter out the NPM bundled dependencies so we aren't providing them
%global __provides_exclude_from ^%{_prefix}/lib/node_modules/npm/.*$
%global __requires_exclude_from ^%{_prefix}/lib/node_modules/npm/.*$


Name: nodejs
Epoch: %{nodejs_epoch}
Version: %{nodejs_version}
Release: %{nodejs_release}%{?dist}
Summary: JavaScript runtime
License: MIT and ASL 2.0 and ISC and BSD
Group: Development/Languages
URL: http://nodejs.org/

ExclusiveArch: %{nodejs_arches}

# nodejs bundles openssl, but we use the system version in Fedora
# because openssl contains prohibited code, we remove openssl completely from
# the tarball, using the script in Source100
Source0: node-v%{nodejs_version}-stripped.tar.gz
Source100: %{name}-tarball.sh

# The native module Requires generator remains in the nodejs SRPM, so it knows
# the nodejs and v8 versions.  The remainder has migrated to the
# nodejs-packaging SRPM.
Source7: nodejs_native.attr

# Disable running gyp on bundled deps we don't use
Patch1: 0001-Disable-running-gyp-files-for-bundled-deps.patch

# EPEL only has OpenSSL 1.0.1, so we need to carry a patch on that platform
Patch2: 0002-Use-openssl-1.0.1.patch

# use system certificates instead of the bundled ones
# Backported from upstream 7.5.0+
Patch3: 0003-crypto-Use-system-CAs-instead-of-using-bundled-ones.patch

# Patch to allow building with GCC 7 from
# https://github.com/nodejs/node/issues/10388#issuecomment-283120731
Patch4: 0004-Fix-compatibility-with-GCC-7.patch

# RHEL 7 still uses OpenSSL 1.0.1 for now, and it segfaults on SSL
# Revert this upstream patch until RHEL 7 upgrades to 1.0.2
Patch5: EPEL01-openssl101-compat.patch

Patch100: 0100-Use-xargs-for-long-commands.patch

BuildRequires: python-devel
BuildRequires: libuv-devel >= 1:1.9.1
Requires: libuv >= 1:1.9.1
BuildRequires: libicu-devel
BuildRequires: zlib-devel
BuildRequires: gcc >= 4.8.0
BuildRequires: gcc-c++ >= 4.8.0
BuildRequires: systemtap-sdt-devel

%if 0%{?rhel} == 7
BuildRequires: openssl-devel >= 1:1.0.1
%else
%if 0%{?fedora} > 25
BuildRequires: compat-openssl10-devel >= 1:1.0.2
%else
BuildRequires: openssl-devel >= 1:1.0.2
%endif
%endif

# we need the system certificate store when Patch2 is applied
Requires: ca-certificates

#we need ABI virtual provides where SONAMEs aren't enough/not present so deps
#break when binary compatibility is broken
Provides: nodejs(abi) = %{nodejs_abi}
Provides: nodejs(abi%{nodejs_major}) = %{nodejs_abi}
Provides: nodejs(v8-abi) = %{v8_abi}
Provides: nodejs(v8-abi%{v8_major}) = %{v8_abi}

#this corresponds to the "engine" requirement in package.json
Provides: nodejs(engine) = %{nodejs_version}

# Node.js currently has a conflict with the 'node' package in Fedora
# The ham-radio group has agreed to rename their binary for us, but
# in the meantime, we're setting an explicit Conflicts: here
Conflicts: node <= 0.3.2-12
Obsoletes: nodejs < 1:6.10.1-2

# The punycode module was absorbed into the standard library in v0.6.
# It still exists as a seperate package for the benefit of users of older
# versions.  Since we've never shipped anything older than v0.10 in Fedora,
# we don't need the seperate nodejs-punycode package, so we Provide it here so
# dependent packages don't need to override the dependency generator.
# See also: RHBZ#11511811
# UPDATE: punycode will be deprecated and so we should unbundle it in Node v8
# and use upstream module instead
# https://github.com/nodejs/node/commit/29e49fc286080215031a81effbd59eac092fff2f
Provides: nodejs-punycode = %{punycode_version}
Provides: npm(punycode) = %{punycode_version}


# Node.js has forked c-ares from upstream in an incompatible way, so we need
# to carry the bundled version internally.
# See https://github.com/nodejs/node/commit/766d063e0578c0f7758c3a965c971763f43fec85
Provides: bundled(c-ares) = %{c_ares_version}

# Node.js is closely tied to the version of v8 that is used with it. It makes
# sense to use the bundled version because upstream consistently breaks ABI
# even in point releases. Node.js upstream has now removed the ability to build
# against a shared system version entirely.
# See https://github.com/nodejs/node/commit/d726a177ed59c37cf5306983ed00ecd858cfbbef
Provides: bundled(v8) = %{v8_version}

# Node.js and http-parser share an upstream. The http-parser upstream does not
# do releases often and is almost always far behind the bundled version
Provides: bundled(http-parser) = %{http_parser_version}

%description
Node.js is a platform built on Chrome's JavaScript runtime
for easily building fast, scalable network applications.
Node.js uses an event-driven, non-blocking I/O model that
makes it lightweight and efficient, perfect for data-intensive
real-time applications that run across distributed devices.

%package devel
Summary: JavaScript runtime - development headers
Group: Development/Languages
Requires: %{name}%{?_isa} = %{epoch}:%{nodejs_version}-%{nodejs_release}%{?dist}
Requires: libuv-devel%{?_isa}
Requires: openssl-devel%{?_isa}
Requires: zlib-devel%{?_isa}
Requires: nodejs-packaging

%description devel
Development headers for the Node.js JavaScript runtime.

%package -n npm
Summary: Node.js Package Manager
Epoch: %{npm_epoch}
Version: %{npm_version}
Release: %{npm_release}%{?dist}

# We used to ship npm separately, but it is so tightly integrated with Node.js
# (and expected to be present on all Node.js systems) that we ship it bundled
# now.
Obsoletes: npm < 0:3.5.4-6
Provides: npm = %{npm_epoch}:%{npm_version}
Requires: nodejs = %{epoch}:%{nodejs_version}-%{nodejs_release}%{?dist}

# Do not add epoch to the virtual NPM provides or it will break
# the automatic dependency-generation script.
Provides: npm(npm) = %{npm_version}

%description -n npm
npm is a package manager for node.js. You can use it to install and publish
your node programs. It manages dependencies and does other cool stuff.

%package docs
Summary: Node.js API documentation
Group: Documentation
BuildArch: noarch

# We don't require that the main package be installed to
# use the docs, but if it is installed, make sure the
# version always matches
Conflicts: %{name} > %{epoch}:%{nodejs_version}-%{nodejs_release}%{?dist}
Conflicts: %{name} < %{epoch}:%{nodejs_version}-%{nodejs_release}%{?dist}

%description docs
The API documentation for the Node.js JavaScript runtime.


%prep
%setup -q -n node-v%{nodejs_version}

# remove bundled dependencies that we aren't building
%patch1 -p1
rm -rf deps/icu-small \
       deps/uv \
       deps/zlib

# Use system CA certificates
%patch3 -p1

# Fix GCC7 build
%patch4 -p1

%if 0%{?epel}
%patch2 -p1
%patch5 -p1
%endif

%patch100 -p0


%build
# build with debugging symbols and add defines from libuv (#892601)
# Node's v8 breaks with GCC 6 because of incorrect usage of methods on
# NULL objects. We need to pass -fno-delete-null-pointer-checks
export CFLAGS='%{optflags} -g \
               -D_LARGEFILE_SOURCE \
               -D_FILE_OFFSET_BITS=64 \
               -DZLIB_CONST \
               -fno-delete-null-pointer-checks'
export CXXFLAGS='%{optflags} -g \
                 -D_LARGEFILE_SOURCE \
                 -D_FILE_OFFSET_BITS=64 \
                 -DZLIB_CONST \
                 -fno-delete-null-pointer-checks'

# Explicit new lines in C(XX)FLAGS can break naive build scripts
export CFLAGS="$(echo ${CFLAGS} | tr '\n\\' '  ')"
export CXXFLAGS="$(echo ${CXXFLAGS} | tr '\n\\' '  ')"

./configure --prefix=%{_prefix} \
           --shared-openssl \
           --shared-zlib \
           --shared-libuv \
           --without-dtrace \
           --with-intl=system-icu \
           --openssl-use-def-ca-store

%if %{?with_debug} == 1
# Setting BUILDTYPE=Debug builds both release and debug binaries
make BUILDTYPE=Debug %{?_smp_mflags}
%else
make BUILDTYPE=Release %{?_smp_mflags}
%endif


%install
rm -rf %{buildroot}

./tools/install.py install %{buildroot} %{_prefix}

# Set the binary permissions properly
chmod 0755 %{buildroot}/%{_bindir}/node

%if %{?with_debug} == 1
# Install the debug binary and set its permissions
install -Dpm0755 out/Debug/node %{buildroot}/%{_bindir}/node_g
%endif

# own the sitelib directory
mkdir -p %{buildroot}%{_prefix}/lib/node_modules

# ensure Requires are added to every native module that match the Provides from
# the nodejs build in the buildroot
install -Dpm0644 %{SOURCE7} %{buildroot}%{_rpmconfigdir}/fileattrs/nodejs_native.attr
cat << EOF > %{buildroot}%{_rpmconfigdir}/nodejs_native.req
#!/bin/sh
echo 'nodejs(abi%{nodejs_major}) >= %nodejs_abi'
echo 'nodejs(v8-abi%{v8_major}) >= %v8_abi'
EOF
chmod 0755 %{buildroot}%{_rpmconfigdir}/nodejs_native.req

#install documentation
mkdir -p %{buildroot}%{_pkgdocdir}/html
cp -pr doc/* %{buildroot}%{_pkgdocdir}/html
rm -f %{buildroot}%{_pkgdocdir}/html/nodejs.1

#node-gyp needs common.gypi too
mkdir -p %{buildroot}%{_datadir}/node
cp -p common.gypi %{buildroot}%{_datadir}/node

# Install the GDB init tool into the documentation directory
mv %{buildroot}/%{_datadir}/doc/node/gdbinit %{buildroot}/%{_pkgdocdir}/gdbinit

# Since the old version of NPM was unbundled, there are a lot of symlinks in
# it's node_modules directory. We need to keep these as symlinks to ensure we
# can backtrack on this if we decide to.

# Rename the npm node_modules directory to node_modules.bundled
mv %{buildroot}/%{_prefix}/lib/node_modules/npm/node_modules \
   %{buildroot}/%{_prefix}/lib/node_modules/npm/node_modules.bundled

# Recreate all the symlinks
mkdir -p %{buildroot}/%{_prefix}/lib/node_modules/npm/node_modules
FILES=%{buildroot}/%{_prefix}/lib/node_modules/npm/node_modules.bundled/*
for f in $FILES
do
  module=`basename $f`
  ln -s ../node_modules.bundled/$module %{buildroot}%{_prefix}/lib/node_modules/npm/node_modules/$module
done

# install NPM docs to mandir
mkdir -p %{buildroot}%{_mandir} \
         %{buildroot}%{_pkgdocdir}/npm

cp -pr deps/npm/man/* %{buildroot}%{_mandir}/
rm -rf %{buildroot}%{_prefix}/lib/node_modules/npm/man
ln -sf %{_mandir}  %{buildroot}%{_prefix}/lib/node_modules/npm/man

# Install Markdown and HTML documentation to %{_pkgdocdir}
cp -pr deps/npm/html deps/npm/doc %{buildroot}%{_pkgdocdir}/npm/
rm -rf %{buildroot}%{_prefix}/lib/node_modules/npm/html \
       %{buildroot}%{_prefix}/lib/node_modules/npm/doc

ln -sf %{_pkgdocdir} %{buildroot}%{_prefix}/lib/node_modules/npm/html
ln -sf %{_pkgdocdir}/npm/html %{buildroot}%{_prefix}/lib/node_modules/npm/doc


%check
# Fail the build if the versions don't match
%{buildroot}/%{_bindir}/node -e "require('assert').equal(process.versions.node, '%{nodejs_version}')"
%{buildroot}/%{_bindir}/node -e "require('assert').equal(process.versions.v8, '%{v8_version}')"
%{buildroot}/%{_bindir}/node -e "require('assert').equal(process.versions.ares.replace(/-DEV$/, ''), '%{c_ares_version}')"
%{buildroot}/%{_bindir}/node -e "require('assert').equal(process.versions.http_parser, '%{http_parser_version}')"

# Ensure we have punycode and that the version matches
%{buildroot}/%{_bindir}/node -e "require(\"assert\").equal(require(\"punycode\").version, '%{punycode_version}')"

# Ensure we have npm and that the version matches
NODE_PATH=%{buildroot}%{_prefix}/lib/node_modules %{buildroot}/%{_bindir}/node -e "require(\"assert\").equal(require(\"npm\").version, '%{npm_version}')"

%files
%{_bindir}/node
%dir %{_prefix}/lib/node_modules
%dir %{_datadir}/node
%dir %{_datadir}/systemtap
%dir %{_datadir}/systemtap/tapset
%{_datadir}/systemtap/tapset/node.stp
%{_rpmconfigdir}/fileattrs/nodejs_native.attr
%{_rpmconfigdir}/nodejs_native.req
%license LICENSE
%doc AUTHORS CHANGELOG.md COLLABORATOR_GUIDE.md GOVERNANCE.md README.md
%doc ROADMAP.md WORKING_GROUPS.md
%doc %{_mandir}/man1/node.1*


%files devel
%if %{?with_debug} == 1
%{_bindir}/node_g
%endif
%{_includedir}/node
%{_datadir}/node/common.gypi
%{_pkgdocdir}/gdbinit


%files -n npm
%{_bindir}/npm
%{_prefix}/lib/node_modules/npm
%ghost %{_sysconfdir}/npmrc
%ghost %{_sysconfdir}/npmignore
%doc %{_mandir}/man*/npm*
%doc %{_mandir}/man5/package.json.5*
%doc %{_mandir}/man7/removing-npm.7*
%doc %{_mandir}/man7/semver.7*


%files docs
%dir %{_pkgdocdir}
%{_pkgdocdir}/html
%{_pkgdocdir}/npm/html
%{_pkgdocdir}/npm/doc

%changelog
* Wed May 10 2017 Brian J. Murrell <brian.murrell@intel.com> 6.10.1-2.04
- new package built with tito

* Mon May 08 2017 Brian J. Murrell <brian.murrell@intel.com> 6.10.1-2.04
- Revert "Handle redefinition of release properly" (brian.murrell@intel.com) 6.10.1-2.04

* Mon May 08 2017 Brian J. Murrell <brian.murrell@intel.com> 6.10.1-2.03
- Bump release to make version superior to previously built packages
  with .git.* in their %{release}

* Sun May 07 2017 Brian J. Murrell <brian.murrell@intel.com> 6.10.1-2.02
- Handle redefinition of release properly (brian.murrell@intel.com)

* Thu May 04 2017 Brian J. Murrell <brian.murrell@intel.com> 6.10.1-2.01
- Rebuild from EPEL as a bridge from the nodesource release to EPEL
  - add a patch to fix building with long paths
  - don't Requires: npm
.
* Mon Apr 03 2017 Stephen Gallagher <sgallagh@redhat.com> - 1:6.10.1-3
- Move NPM manpages into the correct subpackage
- Fixes: rhbx#1433403

* Mon Apr 03 2017 Stephen Gallagher <sgallagh@redhat.com> - 1:6.10.1-2
- Revert upstream change that is incompatible with OpenSSL 1.0.1
- Fixes: rhbz#1436445

* Wed Mar 22 2017 Zuzana Svetlikova <zsvetlik@redhat.com> - 1:6.10.1-1
- Update to 6.10.1
- remove small-icu from deps

* Thu Mar 09 2017 Stephen Gallagher <sgallagh@redhat.com> - 1:6.10.0-1
- Update to 6.10.0
- https://nodejs.org/en/blog/release/v6.10.0/
- New patch for handling system CA certificates

* Tue Feb 28 2017 Stephen Gallagher <sgallagh@redhat.com> - 1:6.9.5-2
- Fix FTBFS against GCC 7
- Resolves: RHBZ 1423991

* Fri Feb 10 2017 Fedora Release Engineering <releng@fedoraproject.org> - 1:6.9.5-1.1
- Rebuilt for https://fedoraproject.org/wiki/Fedora_26_Mass_Rebuild

* Wed Feb 1 2017 Zuzana Svetlikova <zsvetlik@redhat.com> - 1:6.9.5-1
- Update to v6.9.5(security)
- Reenable debug mode (https://github.com/nodejs/node/pull/10525)

* Tue Jan 17 2017 Stephen Gallagher <sgallagh@redhat.com> - 1:6.9.4-2
- Enable DTrace support.
- Eliminate newlines from CFLAGS due to broken dtrace shim
  https://sourceware.org/bugzilla/show_bug.cgi?id=21063
  Thanks to Kinston Hughes for the fix.

* Tue Jan 10 2017 Zuzana Svetlikova <zsvetlik@redhat.com> - 1:6.9.4-1
- Update to v6.9.4

* Thu Jan 05 2017 Stephen Gallagher <sgallagh@redhat.com> - 1:6.9.3-1
- https://nodejs.org/en/blog/release/v6.9.3/

* Wed Dec 21 2016 Stephen Gallagher <sgallagh@redhat.com> - 1:6.9.2-2
- Debug builds are failing. Disable them.

* Thu Dec 08 2016 Zuzana Svetlikova <zsvetlik@redhat.com> - 1:6.9.2-1
- Update to v6.9.2

* Tue Nov 08 2016 Stephen Gallagher <sgallagh@redhat.com> - 1:6.9.1-4
- Fix incorrect Conflicts for nodejs-docs

* Tue Nov 08 2016 Stephen Gallagher <sgallagh@redhat.com> - 1:6.9.1-2
- Bump revision and rebuild for s390x

* Thu Oct 20 2016 Stephen Gallagher <sgallagh@redhat.com> - 1:6.9.1-1
- Update to 6.9.1 LTS release
- Fix a regression introduced in v6.8.0 in readable stream that caused unpipe
  to remove the wrong stream
- https://nodejs.org/en/blog/release/v6.9.1/

* Tue Oct 18 2016 Stephen Gallagher <sgallagh@redhat.com> - -
- Update to 6.9.0 LTS release
- https://nodejs.org/en/blog/release/v6.9.0/

* Mon Oct 17 2016 Stephen Gallagher <sgallagh@redhat.com> - 1:6.8.1-5
- Add dist tag to npm nodejs dependency

* Mon Oct 17 2016 Stephen Gallagher <sgallagh@redhat.com> - 1:6.8.1-4
- Fix typo in npm nodejs dependency

* Sat Oct 15 2016 Stephen Gallagher <sgallagh@redhat.com> - 1:6.8.1-3
- Bump release version for tagging bug

* Sat Oct 15 2016 Stephen Gallagher <sgallagh@redhat.com> - 1:6.8.1-1
- Update node to v6.8.0
- Fix FTBFS against non-bundled zlib

* Thu Oct 13 2016 Zuzana Svetlikova <zsvetlik@redhat.com> - 1:6.8.0-108
- Update node to v6.8.0 and npm@3.10.8

* Tue Sep 27 2016 Stephen Gallagher <sgallagh@redhat.com> - 1:6.7.0-107
- Update to 6.7.0
- https://nodejs.org/en/blog/release/v6.7.0/

* Fri Sep 16 2016 Stephen Gallagher <sgallagh@redhat.com> - 1:6.6.0-106
- Drop Conflicts: from main package.
  It wasn't needed and was breaking upgrades in some cases.
- Move npm support files into the npm package
- Mark manpages as %%doc

* Fri Sep 16 2016 Stephen Gallagher <sgallagh@redhat.com> - 1:6.6.0-105
- Update to 6.6.0
- https://github.com/nodejs/node/blob/v6.6.0/doc/changelogs/CHANGELOG_V6.md#6.6.0

* Mon Sep 12 2016 Stephen Gallagher <sgallagh@redhat.com> - 1:6.5.0-104
- Update to 6.5.0
- Add support for building on EPEL 7 against OpenSSL 1.0.1
- Modify v8_abi autorequires to avoid unnecessary rebuilds

* Fri Jun 24 2016 Zuzana Svetlikova <zsvetlik@redhat.com> - 0.10.46-1
- Update to 0.10.46(security fix)
- https://github.com/nodejs/node/blob/v0.10.46/ChangeLog
- Bump http-parser version

* Wed Feb 10 2016 Stephen Gallagher <sgallagh@redhat.com> - 0.10.43-4
- Verify that the built node reports the expected versions
- Properly Provides: http-parser
- Fix Provides: for punycode

* Wed Feb 10 2016 Stephen Gallagher <sgallagh@redhat.com> - 0.10.42-3
- Remove duplicated content from spec file

* Wed Feb 10 2016 Stephen Gallagher <sgallagh@redhat.com> - 0.10.42-2
- Re-enable debug builds on supported arches

* Wed Feb 10 2016 Stephen Gallagher <sgallagh@redhat.com> - 0.10.42-1
- Update to Node.js 0.10.42
- https://github.com/nodejs/node/blob/v0.10.42/ChangeLog
- Bundle v8, c-ares and http-parser with Node.js
- Drop patches that revert v8 UTF8 change
- Resolves: RHBZ#1306203
- Resolves: RHBZ#1306200
- Resolves: RHBZ#1306207

* Wed Jun 17 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.10.36-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_23_Mass_Rebuild

* Wed Apr 29 2015 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.36-4
- fix incorrect Requires on libuv (RHBZ#1215719)

* Tue Feb 24 2015 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.36-3
- bump v8 requires (RHBZ#1195457)

* Thu Feb 19 2015 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.36-2
- build against compat-libuv010

* Thu Feb 19 2015 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.36-1
- new upstream release 0.10.36
  http://blog.nodejs.org/2015/01/26/node-v0-10-36-stable/
- Please note that several upstream releases were skipped due to regressions
  reported in the upstream bug tracker.  Please also review the 0.10.34 and
  0.10.35 changelogs available at the above URL for a list of all changes.

* Wed Nov 19 2014 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.33-1
- new upstream release 0.10.33
  http://blog.nodejs.org/2014/10/23/node-v0-10-33-stable/
- This release disables SSLv3 to secure Node.js services against the POODLE
  attack.  (CVE-2014-3566; RHBZ#1152789)  For more information or to learn how
  to re-enable SSLv3 in order to support legacy clients, please see the upstream
  release announcement linked above.

* Tue Oct 21 2014 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.32-2
- add Provides nodejs-punycode (RHBZ#1151811)

* Thu Sep 18 2014 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.32-1
- new upstream release 0.10.32
  http://blog.nodejs.org/2014/08/19/node-v0-10-31-stable/
  http://blog.nodejs.org/2014/09/16/node-v0-10-32-stable/

* Sun Aug 17 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.10.30-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_22_Mass_Rebuild

* Fri Aug 01 2014 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.30-1
- new upstream release 0.10.30
  http://blog.nodejs.org/2014/07/31/node-v0-10-30-stable/

* Thu Jun 19 2014 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.29-1
- new upstream release 0.10.29
  http://blog.nodejs.org/2014/06/16/node-v0-10-29-stable/
- The invalid UTF8 fix has been reverted since this breaks v8 API, which cannot
  be done in a stable distribution release.  This build of nodejs will behave as
  if NODE_INVALID_UTF8 was set.  For more information on the implications, see:
  http://blog.nodejs.org/2014/06/16/openssl-and-breaking-utf-8-change/

* Sat Jun 07 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.10.28-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Sat May 03 2014 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.28-2
- use the system certificate store instead of the bundled copy
  both are based on the Mozilla CA list, so the only effect this should have is
  making additional certificates added by the system administrator available to
  node

* Sat May 03 2014 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.28-1
- new upstream release 0.10.28
  There is no dfference between 0.10.27 and 0.10.28 for Fedora, as the only
  thing updated was npm, which is shipped seperately.  The latest was only
  packaged to avoid confusion.  Please see the v0.10.27 changelog for relevant
  changes in this update:
  http://blog.nodejs.org/2014/05/01/node-v0-10-27-stable/

* Thu Feb 20 2014 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.26-1
- new upstream release 0.10.26
  http://blog.nodejs.org/2014/02/18/node-v0-10-26-stable/

* Fri Feb 14 2014 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.25-2
- rebuild for icu-53 (via v8)

* Mon Jan 27 2014 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.25-1
- new upstream release 0.10.25
  http://blog.nodejs.org/2014/01/23/node-v0-10-25-stable/

* Thu Dec 19 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.24-1
- new upstream release 0.10.24
  http://blog.nodejs.org/2013/12/19/node-v0-10-24-stable/
- upstream install script installs the headers now

* Thu Dec 12 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.23-1
- new upstream release 0.10.23
  http://blog.nodejs.org/2013/12/11/node-v0-10-23-stable/

* Tue Nov 12 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.22-1
- new upstream release 0.10.22
  http://blog.nodejs.org/2013/11/12/node-v0-10-22-stable/

* Fri Oct 18 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.21-1
- new upstream release 0.10.21
  http://blog.nodejs.org/2013/10/18/node-v0-10-21-stable/
- resolves an undisclosed security vulnerability in the http module

* Tue Oct 01 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.20-1
- new upstream release 0.10.20
  http://blog.nodejs.org/2013/09/30/node-v0-10-20-stable/

* Wed Sep 25 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.19-1
- new upstream release 0.10.19
  http://blog.nodejs.org/2013/09/24/node-v0-10-19-stable/

* Fri Sep 06 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.18-1
- new upstream release 0.10.18
  http://blog.nodejs.org/2013/09/04/node-v0-10-18-stable/

* Tue Aug 27 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.17-1
- new upstream release 0.10.17
  http://blog.nodejs.org/2013/08/21/node-v0-10-17-stable/
- fix duplicated/conflicting documentation files (RHBZ#1001253)

* Sat Aug 17 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.16-1
- new upstream release 0.10.16
  http://blog.nodejs.org/2013/08/16/node-v0-10-16-stable/
- add v8-devel to -devel Requires
- restrict -devel Requires to the same architecture

* Wed Aug 14 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.14-3
- fix typo in _isa macro in v8 Requires

* Mon Aug 05 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.14-2
- use unversioned docdir for -docs subpackage
  https://fedoraproject.org/wiki/Changes/UnversionedDocdirs
- use main package's docdir instead of a seperate -docs directory

* Thu Jul 25 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.14-1
- new upstream release 0.10.14
  http://blog.nodejs.org/2013/07/25/node-v0-10-14-stable/

* Wed Jul 10 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.13-1
- new upstream release 0.10.13
  http://blog.nodejs.org/2013/07/09/node-v0-10-13-stable/
- remove RPM macros, etc. now that they've migrated to nodejs-packaging

* Wed Jun 19 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.12-1
- new upstream release 0.10.12
  http://blog.nodejs.org/2013/06/18/node-v0-10-12-stable/
- split off a -packaging subpackage with RPM macros, etc.
- build -docs as noarch
- copy mutiple version logic from nodejs-packaging SRPM for now

* Fri May 31 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.9-1
- new upstream release 0.10.9
  http://blog.nodejs.org/2013/05/30/node-v0-10-9-stable/

* Wed May 29 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.8-1
- new upstream release 0.10.8
  http://blog.nodejs.org/2013/05/24/node-v0-10-8-stable/

* Wed May 29 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.7-1
- new upstream release 0.10.7
  http://blog.nodejs.org/2013/05/17/node-v0-10-7-stable/
- strip openssl from the tarball; it contains prohibited code (RHBZ#967736)
- patch Makefile so we can just remove all bundled deps completely

* Wed May 15 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.6-1
- new upstream release 0.10.6
  http://blog.nodejs.org/2013/05/14/node-v0-10-6-stable/

* Mon May 06 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.5-3
- nodejs-fixdep: work properly when a package has no dependencies

* Mon Apr 29 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.5-2
- nodejs-symlink-deps: make it work when --check is used and just
  devDependencies exist

* Wed Apr 24 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.5-1
- new upstream release 0.10.5
  http://blog.nodejs.org/2013/04/23/node-v0-10-5-stable/

* Mon Apr 15 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.4-1
- new upstream release 0.10.4
  http://blog.nodejs.org/2013/04/11/node-v0-10-4-stable/
- add no-op macro to permit spec compatibility with EPEL

* Thu Apr 04 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.3-2
- nodejs-symlink-deps: symlink unconditionally in the buildroot

* Wed Apr 03 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.3-1
- new upstream release 0.10.3
  http://blog.nodejs.org/2013/04/03/node-v0-10-3-stable/
- nodejs-symlink-deps: only create symlink if target exists
- nodejs-symlink-deps: symlink devDependencies when --check is used

* Sun Mar 31 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.2-1
- new upstream release 0.10.2
  http://blog.nodejs.org/2013/03/28/node-v0-10-2-stable/
- remove %%nodejs_arches macro since it will only be useful if it is present in
  the redhat-rpm-config package
- add default filtering macro to remove unwanted Provides from native modules
- nodejs-symlink-deps now supports multiple modules in one SRPM properly
- nodejs-symlink-deps also now supports a --check argument that works in the
  current working directry instead of the buildroot

* Fri Mar 22 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.1-1
- new upstream release 0.10.1
  http://blog.nodejs.org/2013/03/21/node-v0-10-1-stable/

* Wed Mar 20 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.0-4
- fix escaping in dependency generator regular expressions (RHBZ#923941)

* Wed Mar 13 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.10.0-3
- add virtual ABI provides for node and v8 so binary module's deps break when
  binary compatibility is broken
- automatically add matching Requires to nodejs binary modules
- add %%nodejs_arches macro to future-proof ExcluseArch stanza in dependent
  packages

* Tue Mar 12 2013 Stephen Gallagher <sgallagh@redhat.com> - 0.10.0-2
- Fix up documentation subpackage

* Mon Mar 11 2013 Stephen Gallagher <sgallagh@redhat.com> - 0.10.0-1
- Update to stable 0.10.0 release
- https://raw.github.com/joyent/node/v0.10.0/ChangeLog

* Thu Feb 14 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.9.5-11
- Rebuilt for https://fedoraproject.org/wiki/Fedora_19_Mass_Rebuild

* Tue Jan 22 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.9.5-10
- minor bugfixes to RPM magic
  - nodejs-symlink-deps: don't create an empty node_modules dir when a module
    has no dependencies
  - nodes-fixdep: support adding deps when none exist
- Add the full set of headers usually bundled with node as deps to nodejs-devel.
  This way `npm install` for native modules that assume the stuff bundled with
  node exists will usually "just work".
-move RPM magic to nodejs-devel as requested by FPC

* Sat Jan 12 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.9.5-9
- fix brown paper bag bug in requires generation script

* Thu Jan 10 2013 Stephen Gallagher <sgallagh@redhat.com> - 0.9.5-8
- Build debug binary and install it in the nodejs-devel subpackage

* Thu Jan 10 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.9.5-7
- don't use make install since it rebuilds everything

* Thu Jan 10 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.9.5-6
- add %%{?isa}, epoch to v8 deps

* Wed Jan 09 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.9.5-5
- add defines to match libuv (#892601)
- make v8 dependency explicit (and thus more accurate)
- add -g to $C(XX)FLAGS instead of patching configure to add it
- don't write pointless 'npm(foo) > 0' deps

* Sat Jan 05 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.9.5-4
- install development headers
- add nodejs_sitearch macro

* Wed Jan 02 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.9.5-3
- make nodejs-symlink-deps actually work

* Tue Jan 01 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.9.5-2
- provide nodejs-devel so modules can BuildRequire it (and be consistent
  with other interpreted languages in the distro)

* Tue Jan 01 2013 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.9.5-1
- new upstream release 0.9.5
- provide nodejs-devel for the moment
- fix minor bugs in RPM magic
- add nodejs_fixdep macro so packagers can easily adjust dependencies in
  package.json files

* Wed Dec 26 2012 T.C. Hollingsworth <tchollingsworth@gmail.com> - 0.9.4-1
- new upstream release 0.9.4
- system library patches are now upstream
- respect optflags
- include documentation in subpackage
- add RPM dependency generation and related magic
- guard libuv depedency so it always gets bumped when nodejs does
- add -devel subpackage with enough to make node-gyp happy

* Wed Dec 19 2012 Dan Horák <dan[at]danny.cz> - 0.9.3-8
- set exclusive arch list to match v8

* Tue Dec 18 2012 Stephen Gallagher <sgallagh@redhat.com> - 0.9.3-7
- Add remaining changes from code review
- Remove unnecessary BuildRequires on findutils
- Remove %%clean section

* Fri Dec 14 2012 Stephen Gallagher <sgallagh@redhat.com> - 0.9.3-6
- Fixes from code review
- Fix executable permissions
- Correct the License field
- Build debuginfo properly

* Thu Dec 13 2012 Stephen Gallagher <sgallagh@redhat.com> - 0.9.3-5
- Return back to using the standard binary name
- Temporarily adding a conflict against the ham radio node package until they
  complete an agreed rename of their binary.

* Wed Nov 28 2012 Stephen Gallagher <sgallagh@redhat.com> - 0.9.3-4
- Rename binary and manpage to nodejs

* Mon Nov 19 2012 Stephen Gallagher <sgallagh@redhat.com> - 0.9.3-3
- Update to latest upstream development release 0.9.3
- Include upstreamed patches to unbundle dependent libraries

* Tue Oct 23 2012 Adrian Alves <alvesadrian@fedoraproject.org>  0.8.12-1
- Fixes and Patches suggested by Matthias Runge

* Mon Apr 09 2012 Adrian Alves <alvesadrian@fedoraproject.org> 0.6.5
- First build.

