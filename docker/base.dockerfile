FROM centos as builder
WORKDIR /build
COPY . .
RUN yum update -y
RUN yum install -y rpmdevtools make git
RUN make -f .copr/Makefile base.repo

FROM centos:7

ENV HTTPS_FRONTEND_PORT 7443
ENV DB_HOST postgres
ENV DB_PORT 5432
ENV AMQP_BROKER_HOST rabbit
ENV SERVER_FQDN nginx
ENV LOG_PATH .

WORKDIR /usr/share/chroma-manager/
COPY . .
COPY --from=builder /build/base.repo .
RUN yum update -y \
  && yum install -y epel-release \
  && yum install -y python python-pip python-devel postgresql openssl gcc-c++ \
  && pip install -r requirements.txt \
  && yum remove -y gcc-c++ python-pip python-devel \
  && yum clean all

COPY docker/wait-for-dependencies-postgres.sh /usr/local/bin/
ENTRYPOINT [ "wait-for-dependencies-postgres.sh" ]
