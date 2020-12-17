set -x
yum install -y openssl-devel
yum install -y cargo rpm-build git

unset RUSTC_WRAPPER

[ -f /sccache/target/release/sccache ] \
    && echo "sccache already installed. Skipping." \
    || (cd / \
        && rm -rf /sccache \
        && git clone https://github.com/mozilla/sccache.git \
        && cd /sccache \
        && cargo build --release --no-default-features)

sed -i '/^PATH=\$PATH/d' /root/.bash_profile
sed -i '/^export PATH/d' /root/.bash_profile
sed -i '/^export CARGO_HOME/d' /root/.bash_profile
sed -i '/^export SCCACHE_CACHE_SIZE/d' /root/.bash_profile
sed -i '/^export SCCACHE_DIR/d' /root/.bash_profile
sed -i '/^export RUSTC_WRAPPER/d' /root/.bash_profile

cat <<EOF >> /root/.bash_profile
PATH=$PATH:$HOME/bin
export PATH
export CARGO_HOME=/root/.cargo
export SCCACHE_CACHE_SIZE=40G
export SCCACHE_DIR=/root/.cache
export RUSTC_WRAPPER=/sccache/target/release/sccache
EOF

source /root/.bash_profile


cd /integrated-manager-for-lustre \
    && [ "$1" = "--clean" ] && cargo clean || echo "Attempting to build rpm's without cleaning." \
    && RPM_DIST=".$(date '+%s')" make copr-rpms
