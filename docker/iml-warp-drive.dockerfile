FROM rust-iml-base as builder

FROM ubuntu
COPY --from=builder /build/target/release/iml-warp-drive /usr/local/bin
RUN apt-get update \
  && apt-get install -y curl postgresql-client

COPY docker/wait-for-dependencies-postgres.sh /usr/local/bin/
ENTRYPOINT [ "wait-for-dependencies-postgres.sh" ]
CMD ["iml-warp-drive"]
