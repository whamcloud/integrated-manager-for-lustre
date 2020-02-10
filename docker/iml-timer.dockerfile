FROM rust-iml-base as builder

FROM imlteam/systemd-base:5.1.1-dev
COPY --from=builder /build/target/release/iml-timer /bin/
COPY --from=builder /build/target/release/start-stratagem-scan /bin/
COPY docker/iml-timer/iml-timer.service /etc/systemd/system/

RUN systemctl enable iml-timer

CMD ["/usr/sbin/init"]
