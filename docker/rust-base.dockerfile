# syntax=docker/dockerfile:experimental

FROM centos:7
WORKDIR /build
RUN yum update -y \
  && yum install -y gcc openssl openssl-devel epel-release https://download.postgresql.org/pub/repos/yum/reporpms/EL-7-x86_64/pgdg-redhat-repo-latest.noarch.rpm \
  && yum clean all \
  && yum install -y postgresql96-devel cargo wget \
  && yum clean all
RUN wget https://github.com/mozilla/sccache/releases/download/0.2.13/sccache-0.2.13-x86_64-unknown-linux-musl.tar.gz \
  && tar -xzvf sccache-*-x86_64-unknown-linux-musl.tar.gz \
  && mv sccache-*-x86_64-unknown-linux-musl/sccache /usr/bin \
  && rm -rf sccache-*-x86_64-unknown-linux-musl*

ENV PQ_LIB_DIR=/usr/pgsql-9.6/lib
ENV PATH $PATH:/root/.cargo/bin
ENV CARGO_HOME /root/.cargo
ENV RUSTUP_HOME /root/.rustup
ENV SCCACHE_CACHE_SIZE="40G"
ENV SCCACHE_DIR /.cache/sccache
ENV RUSTC_WRAPPER="sccache"

COPY . .
RUN --mount=type=cache,dst=/.cache/sccache \
  cargo build --release --target-dir=/root/target \
  && mkdir -p /build/target/release \
  && cp -R /root/target/release/* /build/target/release/