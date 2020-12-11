FROM rust-iml-base as builder
FROM imlteam/rust-service-base:6.3.0

COPY --from=builder /build/target/release/iml-task-runner /usr/local/bin
COPY docker/wait-for-dependencies-postgres.sh /usr/local/bin/

ENTRYPOINT [ "wait-for-dependencies-postgres.sh" ]
CMD ["iml-task-runner"]
