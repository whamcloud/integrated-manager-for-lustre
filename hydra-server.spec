%define name hydra-server
%define version 0.1
%define unmangled_version 0.1
%define release 1

Summary: The Whamcloud Lustre Monitoring and Adminisration Interface
Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}-%{unmangled_version}.tar.gz
Source1: hydra-server.conf
Source2: hydra-monitor-init.sh
License: Proprietary
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Whamcloud, Inc. <info@whamcloud.com>
Url: http://www.whamcloud.com/
Requires: Django >= 1.3, mod_wsgi, httpd

%description
This is the Whamcloud Monitoring and Adminstration Interface

%prep
%setup -n %{name}-%{unmangled_version}

%build
python setup.py build

%install
make install DESTDIR=$RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT/etc/{init,httpd/conf}.d 
cp %{SOURCE1} $RPM_BUILD_ROOT/etc/httpd/conf.d/hydra-server.conf
cp %{SOURCE2} $RPM_BUILD_ROOT/etc/init.d/hydra-monitor

%clean
rm -rf $RPM_BUILD_ROOT

%post
ed /etc/httpd/conf.d/wsgi.conf <<EOF 2>/dev/null
/^#LoadModule /s/^#\(LoadModule wsgi_module modules\/mod_wsgi.so\)/\1/
w
q
EOF

# create the database
pushd /usr/share/hydra-server >/dev/null
if [ ! -f database.db ]; then
    # but don't clobber one that's already there!
    PYTHONPATH=$(pwd) python manage.py syncdb --noinput >/dev/null
    # make sure a sql.log debug file exists and apache owns it so
    # it can write to it
    touch /tmp/sql.log
    chown apache.apache /tmp/sql.log
    # and the database, of course
    chown apache.apache /usr/share/hydra-server/database.db
    # start apache at boot time
    chkconfig httpd on
fi
popd >/dev/null

chkconfig --add hydra-monitor

%files
%defattr(-,root,root)
%dir %attr(0755,apache,apache)/usr/share/hydra-server
/usr/share/hydra-server/*
/etc/httpd/conf.d/hydra-server.conf
%attr(0755,root,root)/etc/init.d/hydra-monitor
