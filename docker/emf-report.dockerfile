FROM rust-emf-base as builder

FROM emfteam/systemd-base:6.3.0
COPY --from=builder /build/target/release/emf-report /bin/
COPY docker/emf-report/emf-report.service /etc/systemd/system/
COPY docker/emf-report/emf-report.conf /etc/systemd/system/
COPY emf-report.conf /usr/lib/tmpfiles.d/
COPY docker/wait-for-dependencies.sh /usr/local/bin/

RUN systemctl enable emf-report

ENTRYPOINT ["wait-for-dependencies.sh"]

CMD ["/usr/sbin/init"]
