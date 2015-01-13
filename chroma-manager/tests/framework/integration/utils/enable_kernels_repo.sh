# Add the kernels repo
pdsh -l root -R ssh -S -w $(spacelist_to_commalist "$@") "exec 2>&1; set -xe
yum-config-manager --add-repo=http://cobbler/cobbler/kernels
cat << "EOF" >> /etc/yum.repos.d/cobbler_cobbler_kernels.repo
sslverify=0
gpgcheck=0
EOF
" | dshbak -c
if [ ${PIPESTATUS[0]} != 0 ]; then
    exit 1
fi
