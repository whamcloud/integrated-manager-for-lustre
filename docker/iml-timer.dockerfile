FROM centos:7
ENV container docker

COPY _topdir/RPMS/x86_64/rust-iml-timer*.rpm /tmp/
COPY docker/iml-timer/start-stratagem-scan.py /usr/local/bin

RUN yum clean all \
  && yum install -y epel-release \
  && yum install -y  python-pip \
  && pip install requests \
  && yum autoremove -y python-pip \
  && yum install -y /tmp/rust-iml-timer*.rpm \
  && rm -f /tmp/rust-iml-timer*.rpm \
  && systemctl enable iml-timer


STOPSIGNAL SIGRTMIN+3
COPY docker/wait-for-dependencies.sh /usr/local/bin/

ENTRYPOINT ["wait-for-dependencies.sh"]

CMD ["/sbin/init"]
