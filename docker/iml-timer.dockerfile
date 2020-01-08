FROM rust-iml-base as builder

FROM centos:8
COPY --from=builder /build/target/release/iml-timer /bin/
COPY docker/iml-timer/iml-timer.service /etc/systemd/system/
COPY docker/iml-timer/start-stratagem-scan.py /usr/local/bin

ENV container docker
STOPSIGNAL SIGRTMIN+3

RUN (cd /lib/systemd/system/sysinit.target.wants/; for i in *; do [ $i == \
  systemd-tmpfiles-setup.service ] || rm -f $i; done); \
  rm -f /lib/systemd/system/multi-user.target.wants/*;\
  rm -f /etc/systemd/system/*.wants/*;\
  rm -f /lib/systemd/system/local-fs.target.wants/*; \
  rm -f /lib/systemd/system/sockets.target.wants/*udev*; \
  rm -f /lib/systemd/system/sockets.target.wants/*initctl*; \
  rm -f /lib/systemd/system/basic.target.wants/*; \
  rm -f /lib/systemd/system/anaconda.target.wants/*; \
  yum install -y python2; \
  pip2 install requests; \
  systemctl enable iml-timer;

VOLUME ["sys/fs/cgroup"]

CMD ["/usr/sbin/init"]
