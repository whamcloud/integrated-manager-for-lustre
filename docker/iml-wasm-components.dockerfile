FROM rust:1.39 as builder
WORKDIR /build
COPY . .
RUN cd /build/iml-wasm-components && \ 
  rustup target add wasm32-unknown-unknown && \
  cargo install wasm-bindgen-cli && \
  cargo build --target wasm32-unknown-unknown --release && \
  mkdir package && \
  wasm-bindgen target/wasm32-unknown-unknown/release/package.wasm --no-modules --out-dir /build/package --out-name package && \
  rm /build/package/*.ts;

FROM rust:1.39
COPY --from=builder /build/package /usr/share/iml-manager/iml-wasm-components

COPY docker/wait-for-dependencies.sh /usr/local/bin/
ENTRYPOINT [ "wait-for-dependencies.sh" ]