%define managerdir /iml-manager/

Name:       iml-wasm-components
Version:    0.1.2
# Release Start
Release:    1%{?dist}
# Release End
Summary:    WebAssembly components for use in IML GUIs


License:    MIT
URL:        https://github.com/whamcloud/integrated-manager-for-lustre/iml-wasm-components
Source0:    iml-wasm-components.tar

%description
%{summary}.

%prep
%setup -c

%build
#nothing to do

%install
rm -rf %{buildroot}

mkdir -p %{buildroot}%{_datadir}%{managerdir}%{name}
cp package.js %{buildroot}%{_datadir}%{managerdir}%{name}
cp package_bg.wasm %{buildroot}%{_datadir}%{managerdir}%{name}

%clean
rm -rf %{buildroot}

%files
%attr(0644,root,root)%{_datadir}%{managerdir}%{name}/package.js
%attr(0644,root,root)%{_datadir}%{managerdir}%{name}/package_bg.wasm