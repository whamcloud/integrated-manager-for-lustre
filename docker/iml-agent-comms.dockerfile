FROM rust:1.39 as builder
WORKDIR /build
COPY . .
RUN cd iml-agent-comms && cargo build --release

COPY docker/wait-for-dependencies.sh /usr/local/bin/
ENTRYPOINT [ "wait-for-dependencies.sh" ]
CMD ["iml-agent-comms"]
