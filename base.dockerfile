FROM centos as builder
WORKDIR /build
COPY . .
RUN yum install -y rpmdevtools make \
  && make storage_server.repo

FROM python:2.7
WORKDIR /usr/share/chroma-manager/
COPY . .
COPY --from=builder /build/storage_server.repo .
RUN pip install -r requirements.txt