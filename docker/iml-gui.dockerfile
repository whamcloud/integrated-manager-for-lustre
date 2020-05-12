# syntax=docker/dockerfile:experimental

FROM rust:1.45 as builder
WORKDIR /build
COPY . .
RUN rustup target add wasm32-unknown-unknown && \
    curl https://rustwasm.github.io/wasm-pack/installer/init.sh -sSf | sh && \
    apt-get update -y && \
    apt  install -y curl dirmngr apt-transport-https lsb-release ca-certificates && \
    curl -sL https://deb.nodesource.com/setup_12.x | bash - && \
    curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add - && \
    echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list && \
    apt-get update -y && \
    apt-get install -y yarn nodejs

ENV SCCACHE_CACHE_SIZE="40G"
ENV SCCACHE_DIR /.cache/sccache
ENV RUSTC_WRAPPER="sccache"

RUN wget https://github.com/mozilla/sccache/releases/download/0.2.13/sccache-0.2.13-x86_64-unknown-linux-musl.tar.gz \
    && tar -xzvf sccache-*-x86_64-unknown-linux-musl.tar.gz \
    && mv sccache-*-x86_64-unknown-linux-musl/sccache /usr/bin \
    && rm -rf sccache-*-x86_64-unknown-linux-musl*
RUN --mount=type=cache,dst=/.cache/sccache cd /build/iml-gui \
    && yarn install \
    && yarn build:release

FROM ubuntu
COPY --from=builder /build/iml-gui/dist /usr/share/iml-manager/rust-iml-gui