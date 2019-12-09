FROM rust:1.39 as builder
WORKDIR /build
COPY . .
RUN cd iml-manager-cli && cargo build --release

FROM ubuntu
COPY --from=builder /build/target/release/iml /usr/bin

RUN apt-get update \
  && apt-get install -y curl \
  && echo "#! /usr/bin/env bash \n\
  source /root/.profile && /usr/bin/iml \${@:1}" > /usr/local/bin/iml \
  && chmod +x /usr/local/bin/iml


COPY docker/wait-for-dependencies.sh /usr/local/bin/
ENTRYPOINT wait-for-dependencies.sh && cat /var/lib/chroma/iml-settings.conf > ~/.profile && /bin/bash