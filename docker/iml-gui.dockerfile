FROM rust:1.46 as builder
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
    apt-get install -y yarn nodejs && \
    cd /build/iml-gui && \
    yarn install && \
    yarn build:release;

FROM ubuntu
COPY --from=builder /build/iml-gui/dist /usr/share/iml-manager/rust-iml-gui