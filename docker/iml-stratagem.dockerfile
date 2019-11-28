FROM rust:1.39 as builder
WORKDIR /build
COPY . .
RUN cd iml-services/iml-stratagem && cargo build --release

FROM alpine
COPY --from=builder /build/target/release/iml-stratagem /usr/local/bin

COPY docker/wait-for-dependencies.sh /usr/local/bin/
ENTRYPOINT [ "/usr/local/bin/wait-for-dependencies.sh" ]
CMD ["/usr/local/bin/iml-stratagem"]
