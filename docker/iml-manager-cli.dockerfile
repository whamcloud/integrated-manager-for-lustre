FROM rust-iml-base as builder

FROM ubuntu
COPY --from=builder /build/target/release/iml /usr/bin

RUN apt-get update \
  && apt-get install -y curl \
  && rm -rf /var/lib/apt/lists/* \
  && echo "#! /usr/bin/env bash \n\
  source /root/.profile && /usr/bin/iml \${@:1}" > /usr/local/bin/iml \
  && chmod +x /usr/local/bin/iml


COPY docker/wait-for-dependencies.sh /usr/local/bin/
ENTRYPOINT wait-for-dependencies.sh && cat /var/lib/chroma/iml-settings.conf > ~/.profile && /bin/bash