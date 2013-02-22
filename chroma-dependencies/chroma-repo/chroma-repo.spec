%define debug_package %{nil}
%define product_family Chroma
%define release_name Final
%define base_release_version 6
%define full_release_version 6.2

Name:           chroma-repo
Version:        %{base_release_version}
Release:        1
Summary:        %{product_family} repository file
Group:          System Environment/Base
License:        GPLv2

%description
%{product_family} repository files

%build
echo OK

%install
rm -rf $RPM_BUILD_ROOT

# copy yum repos to /etc/yum.repos.d
mkdir -p $RPM_BUILD_ROOT/etc/yum.repos.d
cat <<"EOF1" > $RPM_BUILD_ROOT/etc/yum.repos.d/Chroma.repo
# Chroma.repo
#

[chroma]
name=Chroma
baseurl=https://mirror.whamcloud.com/chroma/el6/$basearch/
gpgcheck=0
sslcacert=/etc/pki/tls/certs/chroma_ca-cacert.pem

[epel]
name=Extra Packages for Enterprise Linux 6 - $basearch
#baseurl=http://download.fedoraproject.org/pub/epel/6/$basearch
mirrorlist=https://mirrors.fedoraproject.org/metalink?repo=epel-6&arch=$basearch
failovermethod=priority
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-EPEL-6
EOF1

mkdir -p $RPM_BUILD_ROOT/etc/pki/tls/certs/ $RPM_BUILD_ROOT/etc/pki/rpm-gpg/
cat <<"EOF2" > $RPM_BUILD_ROOT/etc/pki/tls/certs/chroma_ca-cacert.pem
-----BEGIN CERTIFICATE-----
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
FTybVA==
-----END CERTIFICATE-----
EOF2

cat <<"EOF3" > $RPM_BUILD_ROOT/etc/pki/rpm-gpg/RPM-GPG-KEY-EPEL-6
-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: GnuPG v1.4.5 (GNU/Linux)

mQINBEvSKUIBEADLGnUj24ZVKW7liFN/JA5CgtzlNnKs7sBg7fVbNWryiE3URbn1
JXvrdwHtkKyY96/ifZ1Ld3lE2gOF61bGZ2CWwJNee76Sp9Z+isP8RQXbG5jwj/4B
M9HK7phktqFVJ8VbY2jfTjcfxRvGM8YBwXF8hx0CDZURAjvf1xRSQJ7iAo58qcHn
XtxOAvQmAbR9z6Q/h/D+Y/PhoIJp1OV4VNHCbCs9M7HUVBpgC53PDcTUQuwcgeY6
pQgo9eT1eLNSZVrJ5Bctivl1UcD6P6CIGkkeT2gNhqindRPngUXGXW7Qzoefe+fV
QqJSm7Tq2q9oqVZ46J964waCRItRySpuW5dxZO34WM6wsw2BP2MlACbH4l3luqtp
Xo3Bvfnk+HAFH3HcMuwdaulxv7zYKXCfNoSfgrpEfo2Ex4Im/I3WdtwME/Gbnwdq
3VJzgAxLVFhczDHwNkjmIdPAlNJ9/ixRjip4dgZtW8VcBCrNoL+LhDrIfjvnLdRu
vBHy9P3sCF7FZycaHlMWP6RiLtHnEMGcbZ8QpQHi2dReU1wyr9QgguGU+jqSXYar
1yEcsdRGasppNIZ8+Qawbm/a4doT10TEtPArhSoHlwbvqTDYjtfV92lC/2iwgO6g
YgG9XrO4V8dV39Ffm7oLFfvTbg5mv4Q/E6AWo/gkjmtxkculbyAvjFtYAQARAQAB
tCFFUEVMICg2KSA8ZXBlbEBmZWRvcmFwcm9qZWN0Lm9yZz6JAjYEEwECACAFAkvS
KUICGw8GCwkIBwMCBBUCCAMEFgIDAQIeAQIXgAAKCRA7Sd8qBgi4lR/GD/wLGPv9
qO39eyb9NlrwfKdUEo1tHxKdrhNz+XYrO4yVDTBZRPSuvL2yaoeSIhQOKhNPfEgT
9mdsbsgcfmoHxmGVcn+lbheWsSvcgrXuz0gLt8TGGKGGROAoLXpuUsb1HNtKEOwP
Q4z1uQ2nOz5hLRyDOV0I2LwYV8BjGIjBKUMFEUxFTsL7XOZkrAg/WbTH2PW3hrfS
WtcRA7EYonI3B80d39ffws7SmyKbS5PmZjqOPuTvV2F0tMhKIhncBwoojWZPExft
HpKhzKVh8fdDO/3P1y1Fk3Cin8UbCO9MWMFNR27fVzCANlEPljsHA+3Ez4F7uboF
p0OOEov4Yyi4BEbgqZnthTG4ub9nyiupIZ3ckPHr3nVcDUGcL6lQD/nkmNVIeLYP
x1uHPOSlWfuojAYgzRH6LL7Idg4FHHBA0to7FW8dQXFIOyNiJFAOT2j8P5+tVdq8
wB0PDSH8yRpn4HdJ9RYquau4OkjluxOWf0uRaS//SUcCZh+1/KBEOmcvBHYRZA5J
l/nakCgxGb2paQOzqqpOcHKvlyLuzO5uybMXaipLExTGJXBlXrbbASfXa/yGYSAG
iVrGz9CE6676dMlm8F+s3XXE13QZrXmjloc6jwOljnfAkjTGXjiB7OULESed96MR
XtfLk0W5Ab9pd7tKDR6QHI7rgHXfCopRnZ2VVQ==
=V/6I
-----END PGP PUBLIC KEY BLOCK-----
EOF3

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root)
%config %attr(0644,root,root) /etc/yum.repos.d/*
%attr(0644,root,root) /etc/pki/tls/certs/*
%attr(0644,root,root) /etc/pki/rpm-gpg/RPM-GPG-KEY-EPEL-6

%changelog
* Thu Jun 14 2012 Brian J. Murrell <brian@whamcould.com> - 6-1
- initial release
