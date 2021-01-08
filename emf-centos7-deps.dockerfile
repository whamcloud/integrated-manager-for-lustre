FROM centos:7
WORKDIR /build
ARG toolchain=stable
ENV PATH $PATH:/root/.cargo/bin
ENV CARGO_HOME /root/.cargo
ENV RUSTUP_HOME /root/.rustup
ENV SCCACHE_CACHE_SIZE="40G"
ENV SCCACHE_DIR /.cache/sccache
ENV RUSTC_WRAPPER="sccache"
RUN yum install -y epel-release \
    && yum install -y python python-devel python-setuptools openssl openssl-devel wget gcc make ed rpm-build \
    && yum install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-7-x86_64/pgdg-redhat-repo-latest.noarch.rpm \
    && yum install -y postgresql96-devel \
    && cd /root \
    && curl https://sh.rustup.rs -sSf | sh -s -- -y --default-toolchain $toolchain
RUN wget https://github.com/mozilla/sccache/releases/download/0.2.14/sccache-0.2.14-x86_64-unknown-linux-musl.tar.gz \
    && tar -xzvf sccache-*-x86_64-unknown-linux-musl.tar.gz \
    && mv sccache-*-x86_64-unknown-linux-musl/sccache /usr/bin \
    && rm -rf sccache-*-x86_64-unknown-linux-musl*
RUN $HOME/.cargo/bin/rustup target add wasm32-unknown-unknown \
    && $HOME/.cargo/bin/cargo install -f wasm-bindgen-cli \
    && $HOME/.cargo/bin/cargo install -f wasm-pack
RUN curl -sL https://rpm.nodesource.com/setup_14.x | bash - \
    && yum install -y nodejs \
    && npm i -g npm yarn