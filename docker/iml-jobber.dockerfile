FROM rust-iml-base as builder

FROM jobber
COPY --from=builder /build/target/x86_64-unknown-linux-musl/release/iml-jobber /usr/local/bin
COPY docker/setup-jobber.sh /usr/local/bin

CMD ["setup-jobber.sh"]
