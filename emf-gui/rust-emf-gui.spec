%define managerdir /emf-manager/

Name:       rust-emf-gui
Version:    0.4.0
# Release Start
Release:    1%{?dist}
# Release End
Summary:    EMF GUI interface written in seed


License:    MIT
URL:        https://github.com/whamcloud/exascaler-management-framework/emf-gui
Source0:    emf-gui.tar

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
