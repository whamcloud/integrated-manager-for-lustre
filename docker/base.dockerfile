FROM centos as builder
WORKDIR /build
COPY . .
RUN yum update -y
RUN yum install -y rpmdevtools make git
RUN make storage_server.repo

FROM python:2.7

ENV HTTPS_FRONTEND_PORT 7443
ENV DB_HOST postgres
ENV DB_PORT 5432
ENV AMQP_BROKER_USER chroma
ENV AMQP_BROKER_PASSWORD chroma123
ENV AMQP_BROKER_VHOST chromavhost
ENV AMQP_BROKER_HOST rabbit
ENV SERVER_FQDN nginx

WORKDIR /usr/share/chroma-manager/
COPY . .
COPY --from=builder /build/storage_server.repo .
RUN apt-get update \
    && apt install -y postgresql-client \
    && pip install -r requirements.txt

COPY docker/wait-for-dependencies.sh /usr/local/bin/
ENTRYPOINT [ "wait-for-dependencies.sh" ]