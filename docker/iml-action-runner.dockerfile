FROM rust:1.39 as builder
WORKDIR /build
COPY . .
RUN cd iml-services/iml-action-runner && cargo build --release

FROM rust:1.39
COPY --from=builder /build/target/release/iml-action-runner /usr/local/bin

COPY docker/wait-for-dependencies.sh /usr/local/bin/
ENTRYPOINT [ "wait-for-dependencies.sh" ]
CMD ["iml-action-runner"]
