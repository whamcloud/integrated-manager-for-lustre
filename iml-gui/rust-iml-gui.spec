%define managerdir /iml-manager/

Name:       rust-iml-gui
Version:    0.4.0
# Release Start
Release:    1%{?dist}
# Release End
Summary:    IML GUI interface written in seed


License:    MIT
URL:        https://github.com/whamcloud/integrated-manager-for-lustre/iml-gui
Source0:    iml-gui.tar

%description
%{summary}.

%prep
%setup -c

%build
#nothing to do

%install
rm -rf %{buildroot}

mkdir -p %{buildroot}%{_datadir}%{managerdir}%{name}
mv dist/* %{buildroot}%{_datadir}%{managerdir}%{name}

%clean
rm -rf %{buildroot}

%files
%dir %attr(0755,nginx,nginx)%{_datadir}%{managerdir}%{name}
%attr(0755,nginx,nginx)%{_datadir}%{managerdir}%{name}/*
