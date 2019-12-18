FROM centos:7
ENV container docker

COPY _topdir/RPMS/x86_64/rust-iml-mailbox*.rpm /tmp/

RUN yum clean all \
  && yum install -y epel-release \
  && yum install -y  python-pip \
  && pip install requests \
  && yum autoremove -y python-pip \
  && yum install -y /tmp/rust-iml-mailbox*.rpm \
  && rm -f /tmp/rust-iml-mailbox*.rpm \
  && systemctl enable iml-mailbox


STOPSIGNAL SIGRTMIN+3
COPY docker/wait-for-dependencies.sh /usr/local/bin/

ENTRYPOINT ["wait-for-dependencies.sh"]

CMD ["/sbin/init"]
