FROM rust-iml-base as builder
FROM imlteam/rust-service-base:6.2.0-dev

COPY --from=builder /build/target/release/iml-agent-comms /usr/local/bin
COPY docker/wait-for-dependencies.sh /usr/local/bin

ENTRYPOINT [ "wait-for-dependencies.sh" ]
CMD ["iml-agent-comms"]
