FROM rust:1.39 as builder
WORKDIR /build
COPY . .
RUN cargo build -p iml-warp-drive --release

FROM rust:1.39
COPY --from=builder /build/target/release/iml-warp-drive /usr/local/bin
RUN apt-get update \
  && apt install -y postgresql-client

COPY docker/wait-for-dependencies-postgres.sh /usr/local/bin/
ENTRYPOINT [ "wait-for-dependencies-postgres.sh" ]
CMD ["iml-warp-drive"]
