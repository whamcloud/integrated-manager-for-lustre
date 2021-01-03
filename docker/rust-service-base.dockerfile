FROM centos:8
RUN dnf update -y \
  && dnf install -y postgresql \
  && dnf clean all
