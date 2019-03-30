FROM rust:1.32 as builder
WORKDIR /build
COPY . .
RUN cargo build --release

FROM rust:1.32
COPY --from=builder /build/target/release/iml-warp-drive /usr/local/bin
RUN apt-get update \
    && apt install -y postgresql-client

COPY docker/wait-for-dependencies.sh /usr/local/bin/
ENTRYPOINT [ "wait-for-dependencies.sh" ]
CMD ["iml-warp-drive"]