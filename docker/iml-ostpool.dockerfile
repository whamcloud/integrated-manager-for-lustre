FROM rust-iml-base as builder

FROM ubuntu
COPY --from=builder /build/target/release/iml-ostpool /usr/local/bin

RUN apt-get update \
  && apt-get install -y curl

COPY docker/wait-for-dependencies.sh /usr/local/bin/
ENTRYPOINT [ "wait-for-dependencies.sh" ]
CMD ["iml-ostpool"]
