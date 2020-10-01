FROM rust-iml-base as builder
FROM imlteam/rust-service-base:6.2.0-dev

COPY --from=builder /build/target/release/iml /usr/bin
COPY docker/wait-for-dependencies.sh /usr/local/bin

ENTRYPOINT wait-for-dependencies.sh && /bin/bash