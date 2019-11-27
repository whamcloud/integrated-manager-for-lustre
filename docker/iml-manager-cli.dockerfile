FROM rust:1.39 as builder
WORKDIR /build
COPY . .
RUN cd iml-manager-cli && cargo build --release

FROM alpine
COPY --from=builder /build/target/release/iml /usr/local/bin

COPY docker/wait-for-dependencies.sh /usr/local/bin/
ENTRYPOINT [ "wait-for-dependencies.sh" ]
