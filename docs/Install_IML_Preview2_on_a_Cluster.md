[**Table of Contents**](index.md)

# IML Lustre Preview2 on a Cluster

## Installing IML:

1. Obtain the preview 2 build from https://github.com/intel-hpdd/intel-manager-for-lustre/releases/download/v4.0.0.0P2/iml-4.0.0.0.tar.gz

2. Configure the correct yum repos on each node in the IML cluster:

### Manager node

```
yum-config-manager --enable addon-epel$(rpm --eval %rhel)-x86_64
yum -y install epel-release

yum-config-manager --add-repo https://copr.fedorainfracloud.org/coprs/managerforlustre/manager-for-lustre/repo/epel-7/managerforlustre-manager-for-lustre-epel-7.repo

yum-config-manager --add-repo http://mirror.centos.org/centos/7/extras/x86_64/
ed <<EOF /etc/yum.repos.d/mirror.centos.org_centos_7_extras_x86_64_.repo
/enabled/a
gpgcheck=1
gpgkey=http://mirror.centos.org/centos/RPM-GPG-KEY-CentOS-7
.
wq
EOF
```

### Storage nodes

```
yum-config-manager --enable addon-epel$(rpm --eval %rhel)-x86_64
yum -y install epel-release

yum-config-manager --add-repo https://copr.fedorainfracloud.org/coprs/managerforlustre/manager-for-lustre/repo/epel-7/managerforlustre-manager-for-lustre-epel-7.repo

yum-config-manager --add-repo http://mirror.centos.org/centos/7/extras/x86_64/
ed <<EOF /etc/yum.repos.d/mirror.centos.org_centos_7_extras_x86_64_.repo
/enabled/a
gpgcheck=1
gpgkey=http://mirror.centos.org/centos/RPM-GPG-KEY-CentOS-7
.
wq
EOF

yum-config-manager --add-repo https://build.whamcloud.com/lustre-b2_10_last_successful_server/
sed -i -e '1d' -e '2s/^.*$/[lustre]/' -e '/baseurl/s/,/%2C/g' -e '/enabled/a gpgcheck=0' /etc/yum.repos.d/build.whamcloud.com_lustre-b2_10_last_successful_server_.repo

yum-config-manager --add-repo https://downloads.hpdd.intel.com/public/e2fsprogs/latest/el7/
sed -i -e '1d' -e '2s/^.*$/[e2fsprogs]/' -e '/baseurl/s/,/%2C/g' -e '/enabled/a gpgcheck=0' /etc/yum.repos.d/downloads.hpdd.intel.com_public_e2fsprogs_latest_el7_.repo
```

### Client nodes

```
yum-config-manager --enable addon-epel$(rpm --eval %rhel)-x86_64
yum -y install epel-release

yum-config-manager --add-repo https://copr.fedorainfracloud.org/coprs/managerforlustre/manager-for-lustre/repo/epel-7/managerforlustre-manager-for-lustre-epel-7.repo

yum-config-manager --add-repo http://mirror.centos.org/centos/7/extras/x86_64/
ed <<EOF /etc/yum.repos.d/mirror.centos.org_centos_7_extras_x86_64_.repo
/enabled/a
gpgcheck=1
gpgkey=http://mirror.centos.org/centos/RPM-GPG-KEY-CentOS-7
.
wq
EOF

yum-config-manager --add-repo https://copr.fedorainfracloud.org/coprs/managerforlustre/lustre-client/repo/epel-7/managerforlustre-lustre-client-epel-7.repo

yum-config-manager --add-repo https://downloads.hpdd.intel.com/public/e2fsprogs/latest/el7/
sed -i -e '1d' -e '2s/^.*$/[e2fsprogs]/' -e '/baseurl/s/,/%2C/g' -e '/enabled/a gpgcheck=0' /etc/yum.repos.d/downloads.hpdd.intel.com_public_e2fsprogs_latest_el7_.repo
```

3. Upload the IML tarball to manager node and install

```
tar -xzf iml-4.0.0.0.tar.gz
cd iml-4.0.0.0
./install
```