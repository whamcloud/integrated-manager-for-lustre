FROM centos:7 as builder
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
ENV IML_API_HOST iml-api

WORKDIR /usr/share/chroma-manager/
COPY . .
COPY --from=builder /build/base.repo .
RUN yum update -y \
  && yum install -y epel-release https://download.postgresql.org/pub/repos/yum/reporpms/EL-7-x86_64/pgdg-redhat-repo-latest.noarch.rpm \
  && yum clean all \
  && yum install -y python python-pip python-devel python2-pbr postgresql96 openssl gcc-c++ \
  && pip install -r requirements.txt \
  && yum autoremove -y gcc-c++ python-pip python-devel \
  && rm -rf /root/.cache/pip \
  && yum install -y python-setuptools \
  && yum clean all

COPY docker/wait-for-dependencies-postgres.sh /usr/local/bin/
ENTRYPOINT [ "wait-for-dependencies-postgres.sh" ]
