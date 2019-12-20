FROM grafana/grafana
USER root
RUN apk add postgresql-client curl python \
  && mkdir -p /usr/share/chroma-manager/grafana/dashboards/

COPY docker/grafana/setup-grafana /usr/share/grafana/
COPY docker/grafana/setup-grafana.sh /usr/local/bin/
COPY grafana/grafana-iml.ini /etc/grafana/grafana.ini
COPY docker/grafana/provisioning/datasources/* /etc/grafana/provisioning/datasources/
COPY grafana/dashboards/iml-dashboards.yaml /etc/grafana/provisioning/dashboards/
COPY grafana/dashboards/iml-dashboards-1.json /usr/share/chroma-manager/grafana/dashboards/
COPY docker/wait-for-dependencies-postgres.sh /usr/bin/

ENTRYPOINT [ "wait-for-dependencies-postgres.sh" ]
CMD ["setup-grafana.sh"]
