FROM centos:7
ENV container docker

RUN yum-config-manager --add-repo=https://copr.fedorainfracloud.org/coprs/managerforlustre/iml-manager-scheduler/repo/epel-7/managerforlustre-iml-manager-scheduler-epel-7.repo \
  && yum clean all \
  && yum install -y rust-iml-jobber \
  && systemctl enable iml-jobber
 

STOPSIGNAL SIGRTMIN+3
COPY docker/jobber-settings.conf /var/lib/chroma/

ENTRYPOINT ["/sbin/init"]
