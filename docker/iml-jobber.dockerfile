FROM centos:7
ENV container docker

COPY _topdir/RPMS/x86_64/rust-iml-jobber*.rpm /tmp/
COPY docker/iml-jobber/start-stratagem-scan.py /usr/local/bin

RUN yum-config-manager --add-repo=https://copr.fedorainfracloud.org/coprs/managerforlustre/iml-manager-scheduler/repo/epel-7/managerforlustre-iml-manager-scheduler-epel-7.repo \
  && yum clean all \
  && yum install -y epel-release python-pip \
  && pip install requests \
  && yum install -y /tmp/rust-iml-jobber*.rpm \
  && systemctl enable iml-jobber


STOPSIGNAL SIGRTMIN+3
COPY docker/jobber-settings.conf /var/lib/chroma/

ENTRYPOINT ["/sbin/init"]
