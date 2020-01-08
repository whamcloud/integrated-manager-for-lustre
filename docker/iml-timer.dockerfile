FROM rust-iml-base as builder

FROM imlteam/systemd-base
COPY --from=builder /build/target/release/iml-timer /bin/
COPY docker/iml-timer/iml-timer.service /etc/systemd/system/
COPY docker/iml-timer/start-stratagem-scan.py /usr/local/bin


RUN yum install -y epel-release \
  && yum install -y python2 \
  && pip2 install requests \
  && systemctl enable iml-timer

CMD ["/usr/sbin/init"]
