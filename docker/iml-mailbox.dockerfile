FROM rust-iml-base as builder

FROM centos:7
COPY --from=builder /build/target/release/iml-mailbox /usr/local/bin
COPY iml-mailbox.service /etc/systemd/system/iml-mailbox.service
COPY docker/iml-mailbox/iml-mailbox-overrides.conf /etc/systemd/system/iml-mailbox.d/iml-mailbox-overrides.conf

ENV container docker

RUN systemctl enable iml-mailbox


STOPSIGNAL SIGRTMIN+3
COPY docker/wait-for-dependencies.sh /usr/local/bin/

ENTRYPOINT ["wait-for-dependencies.sh"]

CMD ["/sbin/init"]
