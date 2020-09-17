FROM rust-iml-base as builder

FROM imlteam/systemd-base:6.2.0-dev
COPY --from=builder /build/target/release/iml-timer /bin/
COPY --from=builder /build/target/release/iml /usr/bin
COPY docker/iml-timer/iml-timer.service /etc/systemd/system/

RUN systemctl enable iml-timer

CMD ["/usr/sbin/init"]
