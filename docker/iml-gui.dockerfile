FROM rust:1.41 as builder
WORKDIR /build
COPY . .
RUN cd /build/iml-gui && \
    curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add - && \
    echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list && \
    curl -sL https://deb.nodesource.com/setup_12.x | bash - && \
    apt-get install -y yarn nodejs && \
    rustup target add wasm32-unknown-unknown && \
    curl https://rustwasm.github.io/wasm-pack/installer/init.sh -sSf | sh && \
    yarn install && \
    yarn build:release;

FROM ubuntu
COPY --from=builder /build/iml-gui/dist /usr/share/iml-manager/rust-iml-gui

COPY docker/wait-for-dependencies.sh /usr/local/bin/
ENTRYPOINT [ "wait-for-dependencies.sh" ]