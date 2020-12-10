FROM rust-iml-base as builder

FROM imlteam/systemd-base:6.3.0
COPY --from=builder /build/target/release/iml-report /bin/
COPY docker/iml-report/iml-report.service /etc/systemd/system/
COPY docker/iml-report/iml-report.conf /etc/systemd/system/
COPY iml-report.conf /usr/lib/tmpfiles.d/
COPY docker/wait-for-dependencies.sh /usr/local/bin/

RUN systemctl enable iml-report

ENTRYPOINT ["wait-for-dependencies.sh"]

CMD ["/usr/sbin/init"]
