FROM rust:1.39 as builder
WORKDIR /build
COPY . .
RUN cd iml-agent-comms && cargo build --release

FROM ubuntu
COPY --from=builder /build/target/release/iml-agent-comms /usr/local/bin

RUN apt-get update \
  && apt-get install -y curl

COPY docker/wait-for-dependencies.sh /usr/local/bin/
ENTRYPOINT [ "wait-for-dependencies.sh" ]
CMD ["iml-agent-comms"]
