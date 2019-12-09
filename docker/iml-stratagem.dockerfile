FROM rust:1.39 as builder
WORKDIR /build
COPY . .
RUN cd iml-services/iml-stratagem && cargo build --release

FROM ubuntu
COPY --from=builder /build/target/release/iml-stratagem /usr/local/bin

RUN apt-get update \
  && apt-get install -y curl

COPY docker/wait-for-dependencies.sh /usr/local/bin/
ENTRYPOINT [ "wait-for-dependencies.sh" ]
CMD ["iml-stratagem"]
