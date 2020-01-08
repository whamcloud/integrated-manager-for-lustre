FROM rust:1.40
WORKDIR /build
COPY . .
RUN rustup target add x86_64-unknown-linux-musl \
  && cd /build/iml-jobber \
  && cargo build --release --target x86_64-unknown-linux-musl \
  && cd /build \
  && cargo build --release