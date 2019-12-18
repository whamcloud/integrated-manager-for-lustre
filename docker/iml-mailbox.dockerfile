FROM rust-iml-base as builder

FROM ubuntu
COPY --from=builder /build/target/release/iml-mailbox /usr/local/bin

CMD ["iml-mailbox"]
