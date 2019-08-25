FROM rust:1.36 as builder
WORKDIR /build
COPY . .
RUN cargo build -p iml-warp-drive --release

FROM rust:1.36
COPY --from=builder /build/target/release/iml-warp-drive /usr/local/bin
RUN apt-get update \
    && apt install -y postgresql-client

COPY docker/wait-for-dependencies.sh /usr/local/bin/
ENTRYPOINT [ "wait-for-dependencies.sh" ]
CMD ["iml-warp-drive"]