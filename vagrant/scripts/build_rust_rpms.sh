yum install -y openssl-devel
yum install -y cargo rpm-build

[ -f /root/.cargo/bin/sccache ] && echo "sccache already installed. Skipping." || cargo install sccache

cd /integrated-manager-for-lustre && make copr-rpms
