yum install -y openssl-devel
yum install -y cargo rpm-build

[ -f /root/.cargo/bin/sccache ] && echo "sccache already installed. Skipping." || cargo install sccache

cd /integrated-manager-for-lustre \
    && CARGO_HOME="/root/.cargo" SCCACHE_CACHE_SIZE="40G"  SCCACHE_DIR="/root/.cache" RUSTC_WRAPPER="/root/.cargo/bin/sccache" make copr-rpms
