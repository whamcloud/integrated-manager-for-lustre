FROM rust-iml-base as builder

FROM imlteam/systemd-base:6.3.0
COPY --from=builder /build/target/release/iml-timer /bin/
COPY --from=builder /build/target/release/iml /usr/bin
COPY docker/iml-timer/iml-timer.service /usr/lib/systemd/system/
COPY docker/wait-for-settings.sh /usr/local/bin/

RUN systemctl enable iml-timer

ENTRYPOINT ["wait-for-settings.sh"]
CMD ["/usr/sbin/init"]
