[**Intel® Manager for Lustre\* Developer Resources Table of Contents**](index.md)

IML preview 1 requires repo files to be setup on each node prior to use.  Different nodes have different repo requirements. A tool like PDSH can be used to setup multiple nodes at once. The repo configs are as follows:

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

### Storage node

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

### Client node

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