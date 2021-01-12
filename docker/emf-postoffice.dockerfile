FROM rust-emf-base as builder
FROM emfteam/rust-service-base:6.3.0

COPY --from=builder /build/target/release/emf-postoffice /usr/local/bin
COPY docker/wait-for-dependencies.sh /usr/local/bin/

ENTRYPOINT [ "wait-for-dependencies.sh" ]
CMD ["emf-postoffice"]
