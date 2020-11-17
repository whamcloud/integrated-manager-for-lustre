yum install -y openssl-devel
yum install -y cargo rpm-build

[ -f /root/.cargo/bin/sccache ] && echo "sccache already installed. Skipping." || cargo install sccache

cd /integrated-manager-for-lustre \
    && sed -i 's/Release: 1.*/Release: 1.'"$(date '+%s')"'/g' rust-iml.spec \
    && make copr-rpms
