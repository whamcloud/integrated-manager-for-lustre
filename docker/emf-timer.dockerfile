FROM rust-emf-base as builder

FROM emfteam/systemd-base:6.3.0
COPY --from=builder /build/target/release/emf-timer /bin/
COPY --from=builder /build/target/release/emf /usr/bin
COPY docker/emf-timer/emf-timer.service /usr/lib/systemd/system/
COPY docker/wait-for-settings.sh /usr/local/bin/

RUN systemctl enable emf-timer

ENTRYPOINT ["wait-for-settings.sh"]
CMD ["/usr/sbin/init"]
