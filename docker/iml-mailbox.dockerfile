FROM rust-iml-base as builder

FROM centos:8
COPY --from=builder /build/target/release/iml-mailbox /bin/
COPY docker/iml-mailbox/iml-mailbox.service /etc/systemd/system/
COPY docker/iml-mailbox/iml-mailbox.conf /etc/systemd/system/
COPY iml-mailbox.conf /usr/lib/tmpfiles.d/
COPY docker/wait-for-dependencies.sh /usr/local/bin/

ENV container docker
STOPSIGNAL SIGRTMIN+3

RUN systemctl enable iml-mailbox

ENTRYPOINT ["wait-for-dependencies.sh"]

CMD ["/sbin/init"]
