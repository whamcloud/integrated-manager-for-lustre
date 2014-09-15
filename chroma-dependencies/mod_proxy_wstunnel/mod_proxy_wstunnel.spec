Name:           mod_proxy_wstunnel
Version:        0.1
Release:        2%{?dist}
Summary:        Websockets support module for mod_proxy

Group:          System Environment/Libraries
License:        ASL 2.0
URL:            http://http://httpd.apache.org/docs/2.4/mod/mod_proxy_wstunnel.html
Source0:        %{name}-%{version}.tar.gz
Source1:        proxy_wstunnel.conf
Patch1: mod_proxy_wstunnel-0.1-warnings.patch
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires:  httpd-devel
Requires: httpd

%description
This module requires the service of mod_proxy. It provides support for the tunnelling of web socket connections to a backend websockets server. This module was backported from the apache 2.4 line for apache 2.2 in EL6.


%prep
%setup -q
%patch1 -p1 -b .warnings

%build
export CFLAGS="-fno-strict-aliasing"
%configure
make %{?_smp_mflags}


%install
rm -rf $RPM_BUILD_ROOT
make install DESTDIR=$RPM_BUILD_ROOT

install -d -m 755 $RPM_BUILD_ROOT%{_sysconfdir}/httpd/conf.d
install -p -m 644 %{SOURCE1} $RPM_BUILD_ROOT%{_sysconfdir}/httpd/conf.d/


%clean
rm -rf $RPM_BUILD_ROOT


%files
%defattr(-,root,root,-)
%doc LICENSE README
%config(noreplace) %{_sysconfdir}/httpd/conf.d/proxy_wstunnel.conf
%{_libdir}/httpd/modules/mod_proxy_wstunnel.so


%changelog
* Wed Dec 11 2013 Michael MacDonald <michael.macdonald@intel.com> - 0.1-1
- Initial packaging for EL6

 * Fri Sep 26 2014 Joe Grund <joe.grund@intel.com> - 0.1-2
- Update with fixes from httpd 2.4.10
