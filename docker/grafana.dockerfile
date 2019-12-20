FROM grafana/grafana
USER root
RUN apk add postgresql-client curl python \
  && mkdir -p /var/lib/grafana/dashboards/

COPY docker/grafana/setup-grafana /usr/share/grafana/
COPY docker/grafana/setup-grafana.sh /usr/local/bin/
COPY docker/grafana/grafana.ini /etc/grafana/
COPY docker/grafana/provisioning/datasources/* /etc/grafana/provisioning/datasources/
COPY docker/grafana/provisioning/dashboards/* /etc/grafana/provisioning/dashboards/
COPY docker/grafana/dashboards/* /var/lib/grafana/dashboards/
COPY docker/wait-for-dependencies-postgres.sh /usr/bin/

ENTRYPOINT [ "wait-for-dependencies-postgres.sh" ]
CMD ["setup-grafana.sh"]
