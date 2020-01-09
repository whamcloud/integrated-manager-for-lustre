FROM centos:7
RUN yum-config-manager --add-repo=https://copr.fedorainfracloud.org/coprs/managerforlustre/iml-manager-scheduler/repo/epel-7/managerforlustre-iml-manager-scheduler-epel-7.repo \
  && yum install -y rust-iml-jobber \
  && systemctl enable iml-jobber \
  && systemctl start iml-jobber

CMD ["/sbin/init"]
