FROM rust:1.36 as builder
WORKDIR /build
COPY iml-wasm-components .
RUN rustup target add wasm32-unknown-unknown && \
  cargo install wasm-bindgen-cli && \
  cargo build --target wasm32-unknown-unknown --release && \
  mkdir package && \
  wasm-bindgen target/wasm32-unknown-unknown/release/package.wasm --no-modules --out-dir ./package --out-name package && \
  rm /build/package/*.ts;

FROM rust:1.36
COPY --from=builder /build/package /usr/share/iml-manager/iml-wasm-components

COPY docker/wait-for-dependencies.sh /usr/local/bin/
ENTRYPOINT [ "wait-for-dependencies.sh" ]