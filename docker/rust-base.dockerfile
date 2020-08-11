FROM centos:7
WORKDIR /build
ARG toolchain=stable
RUN yum update -y \
  && yum install -y gcc openssl openssl-devel epel-release https://download.postgresql.org/pub/repos/yum/reporpms/EL-7-x86_64/pgdg-redhat-repo-latest.noarch.rpm \
  && yum clean all \
  && yum install -y postgresql96-devel \
  && yum clean all \
  && cd /root \
  && curl https://sh.rustup.rs -sSf | sh -s -- -y --default-toolchain $toolchain

ENV PATH $PATH:/root/.cargo/bin
ENV CARGO_HOME /root/.cargo
ENV RUSTUP_HOME /root/.rustup
ENV PQ_LIB_DIR=/usr/pgsql-9.6/lib
COPY . .
RUN cargo build --release