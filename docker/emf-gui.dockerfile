FROM rust:1.48 as builder
WORKDIR /build
RUN rustup target add wasm32-unknown-unknown && \
    curl https://rustwasm.github.io/wasm-pack/installer/init.sh -sSf | sh && \
    apt-get update -y && \
    apt-get install -y curl dirmngr apt-transport-https lsb-release ca-certificates && \
    curl -sL https://deb.nodesource.com/setup_14.x | bash - && \
    curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add - && \
    echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list && \
    apt-get update -y && \
    apt-get install -y yarn nodejs
COPY . .
RUN cd /build/emf-gui && \
    yarn install && \
    yarn build:release

FROM debian:buster-slim
COPY --from=builder /build/emf-gui/dist /usr/share/emf-manager/rust-emf-gui