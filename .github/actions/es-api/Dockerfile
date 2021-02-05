FROM centos:centos7
RUN yum install python2 -y

WORKDIR /build
ARG toolchain=stable
RUN yum update -y \
  && yum install -y gcc openssl openssl-devel epel-release file diffutils pkgconfig \
  && yum install -y libsodium libsodium-devel \
  && yum clean all \
  && cd /root \
  && curl https://sh.rustup.rs -sSf | sh -s -- -y --default-toolchain $toolchain
ENV PATH $PATH:/root/.cargo/bin
ENV CARGO_HOME /root/.cargo
ENV RUSTUP_HOME /root/.rustup
ENV SODIUM_USE_PKG_CONFIG 1

ADD exascaler_api.tar.gz /usr/lib/python2.7/site-packages/

COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]