FROM rust-iml-base as builder
FROM imlteam/rust-service-base:6.3.0

COPY --from=builder /build/target/release/iml-api /usr/local/bin
COPY docker/wait-for-dependencies.sh /usr/local/bin/

ENTRYPOINT [ "wait-for-dependencies.sh" ]
CMD ["iml-api"]
