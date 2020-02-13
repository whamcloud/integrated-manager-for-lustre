FROM centos:7
RUN yum update -y \
  && yum install -y postgresql \
  && yum clean all
