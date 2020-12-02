yum install -y openssl-devel
yum install -y cargo rpm-build

[ -f /root/.cargo/bin/sccache ] && echo "sccache already installed. Skipping." || cargo install sccache

sed -i '/^export CARGO_HOME/d' /root/.bash_profile
sed -i '/^export SCCACHE_CACHE_SIZE/d' /root/.bash_profile
sed -i '/^export SCCACHE_DIR/d' /root/.bash_profile
sed -i '/^export RUSTC_WRAPPER/d' /root/.bash_profile

cat <<EOF >> /root/.bash_profile
export CARGO_HOME=/root/.cargo
export SCCACHE_CACHE_SIZE=40G
export SCCACHE_DIR=/root/.cache
export RUSTC_WRAPPER=/root/.cargo/bin/sccache
EOF

source /root/.bash_profile

cd /integrated-manager-for-lustre \
    && RPM_DIST=".$(date '+%s')" make copr-rpms
