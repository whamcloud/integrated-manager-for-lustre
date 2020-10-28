set -x

yum install -y mock-1.2.17 nosync

set +e

useradd mocker
usermod -a -G mock mocker

mkdir -p /home/mocker/.cargo
mkdir -p /home/mocker/target

set -e

new=/etc/mock/iml.cfg.new
old=/etc/mock/iml.cfg

cat << EOF > $new
config_opts['root'] = 'epel-7-x86_64'
config_opts['target_arch'] = 'x86_64'
config_opts['legal_host_arches'] = ('x86_64',)
config_opts['chroot_setup_cmd'] = 'install @buildsys-build'
config_opts['dist'] = 'el7'  # only useful for --resultdir variable subst
config_opts['releasever'] = '7'

config_opts['plugin_conf']['bind_mount_enable'] = True
config_opts['plugin_conf']['bind_mount_opts']['dirs'].append(('/home/mocker/.cargo', '/tmp/.cargo' ))
config_opts['plugin_conf']['bind_mount_opts']['dirs'].append(('/home/mocker/target', '/tmp/target' ))
config_opts['nosync'] = True

config_opts['yum.conf'] = """
[main]
keepcache=1
debuglevel=2
reposdir=/dev/null
logfile=/var/log/yum.log
retries=20
obsoletes=1
gpgcheck=0
assumeyes=1
syslog_ident=mock
syslog_device=
mdpolicy=group:primary

# repos
[base]
name=BaseOS
mirrorlist=http://mirrorlist.centos.org/?release=7&arch=x86_64&repo=os
failovermethod=priority
gpgkey=file:///etc/pki/mock/RPM-GPG-KEY-CentOS-7
gpgcheck=1

[updates]
name=updates
enabled=1
mirrorlist=http://mirrorlist.centos.org/?release=7&arch=x86_64&repo=updates
failovermethod=priority
gpgkey=file:///etc/pki/mock/RPM-GPG-KEY-CentOS-7
gpgcheck=1

[epel]
name=epel
mirrorlist=http://mirrors.fedoraproject.org/mirrorlist?repo=epel-7&arch=x86_64
failovermethod=priority
gpgkey=file:///etc/pki/mock/RPM-GPG-KEY-EPEL-7
gpgcheck=1

[extras]
name=extras
mirrorlist=http://mirrorlist.centos.org/?release=7&arch=x86_64&repo=extras
failovermethod=priority
gpgkey=file:///etc/pki/mock/RPM-GPG-KEY-EPEL-7
gpgcheck=1

[testing]
name=epel-testing
enabled=0
mirrorlist=http://mirrors.fedoraproject.org/mirrorlist?repo=testing-epel7&arch=x86_64
failovermethod=priority


[local]
name=local
baseurl=http://kojipkgs.fedoraproject.org/repos/epel7-build/latest/x86_64/
cost=2000
enabled=0

[epel-debug]
name=epel-debug
mirrorlist=http://mirrors.fedoraproject.org/mirrorlist?repo=epel-debug-7&arch=x86_64
failovermethod=priority
enabled=0

[copr:copr.fedorainfracloud.org:managerforlustre:buildtools]
name=Copr repo for buildtools owned by managerforlustre
baseurl=https://download.copr.fedorainfracloud.org/results/managerforlustre/buildtools/epel-7-x86_64/
type=rpm-md
skip_if_unavailable=True
gpgcheck=1
gpgkey=https://download.copr.fedorainfracloud.org/results/managerforlustre/buildtools/pubkey.gpg
repo_gpgcheck=0
enabled=1
enabled_metadata=1

[zfs]
name=ZFS on Linux for EL7 - dkms
baseurl=http://download.zfsonlinux.org/epel/7.6/x86_64/
enabled=1
gpgcheck=0
"""
EOF

if ! cmp --silent $old $new; then
    mv $new $old;
fi

rm -rf /tmp/iml/_topdir/

su -l mocker << EOF
mock -r /etc/mock/iml.cfg --init
mock -r /etc/mock/iml.cfg --copyin /integrated-manager-for-lustre /iml
mock -r /etc/mock/iml.cfg -i cargo git ed epel-release python-setuptools gcc openssl-devel python2-devel python2-setuptools ed zfs libzfs2-devel
mock -r /etc/mock/iml.cfg --shell 'export CARGO_HOME=/tmp/.cargo CARGO_TARGET_DIR=/tmp/target && cd /iml && make local'
mock -r /etc/mock/iml.cfg --copyout /iml/_topdir /tmp/iml/_topdir
mock -r /etc/mock/iml.cfg --copyout /iml/chroma_support.repo /tmp/iml/
EOF

rm -rf /tmp/{manager,agent}-rpms
mkdir -p /tmp/{manager,agent}-rpms

cp /tmp/iml/_topdir/RPMS/rust-iml-{action-runner,agent-comms,api,cli,corosync,config-cli,journal,mailbox,network,ntp,ostpool,postoffice,report,sfa,snapshot,stats,task-runner,device,warp-drive,timer}-*.rpm /tmp/manager-rpms/
cp /tmp/iml/_topdir/RPMS/python2-iml-manager-*.rpm /tmp/manager-rpms/
cp /tmp/iml/_topdir/RPMS/rust-iml-agent-[0-9]*.rpm /tmp/agent-rpms
cp /tmp/iml/_topdir/RPMS/iml-device-scanner-*.rpm /tmp/agent-rpms
cp /tmp/iml/chroma_support.repo /etc/yum.repos.d/

yum install -y /tmp/manager-rpms/*.rpm

chroma-config setup admin lustre localhost --no-dbspace-check -v
