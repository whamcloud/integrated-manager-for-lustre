FROM rust-iml-base as builder
FROM imlteam/rust-service-base:5.1.1-dev

COPY --from=builder /build/target/release/iml /usr/bin
COPY docker/wait-for-dependencies.sh /usr/local/bin

RUN echo -e "#! /usr/bin/env bash\n\
  source /root/.profile && /usr/bin/iml \${@:1}\n\
  " > /usr/local/bin/iml && chmod +x /usr/local/bin/iml

ENTRYPOINT wait-for-dependencies.sh && cat /var/lib/chroma/iml-settings.conf > ~/.profile && /bin/bash