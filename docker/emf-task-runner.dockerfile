FROM rust-emf-base as builder
FROM emfteam/rust-service-base:6.3.0

COPY --from=builder /build/target/release/emf-task-runner /usr/local/bin
COPY docker/wait-for-dependencies-postgres.sh /usr/local/bin/

ENTRYPOINT [ "wait-for-dependencies-postgres.sh" ]
CMD ["emf-task-runner"]
