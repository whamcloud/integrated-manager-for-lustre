FROM rust:nightly as builder
WORKDIR /build
COPY . .
RUN cargo build -p iml-warp-drive --release

FROM rust:nightly
COPY --from=builder /build/target/release/iml-warp-drive /usr/local/bin
RUN apt-get update \
    && apt install -y postgresql-client

COPY docker/wait-for-dependencies.sh /usr/local/bin/
ENTRYPOINT [ "wait-for-dependencies.sh" ]
CMD ["iml-warp-drive"]