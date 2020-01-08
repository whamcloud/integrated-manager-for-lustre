FROM rust-iml-base as builder

FROM jobber
COPY --from=builder /build/target/release/iml-jobber /usr/local/bin
COPY docker/setup-jobber.sh /usr/local/bin
CMD setup-jobber.sh
