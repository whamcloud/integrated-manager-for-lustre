FROM grafana/grafana
USER root
RUN apk add postgresql-client curl python2 \
  && mkdir -p /usr/share/chroma-manager/grafana/dashboards/

COPY docker/grafana/setup-grafana /usr/share/grafana/
COPY docker/grafana/setup-grafana.sh /usr/local/bin/
COPY grafana/grafana-emf.ini /etc/grafana/grafana.ini
COPY grafana/datasources/influxdb-emf-datasource.yml /etc/grafana/provisioning/datasources/
COPY grafana/dashboards/emf-dashboards.yaml /etc/grafana/provisioning/dashboards/
COPY grafana/dashboards/stratagem-dashboard-1.json /usr/share/chroma-manager/grafana/dashboards/
COPY grafana/dashboards/emf-metrics.json /usr/share/chroma-manager/grafana/dashboards/
COPY docker/wait-for-dependencies-postgres.sh /usr/bin/

# Remove whitelist entry from grafana config as docker will not work with a whitelist
RUN sed -i '/^whitelist/d' /etc/grafana/grafana.ini \
  && sed -i 's/.*url: http:\/\/localhost:8086/    url: http:\/\/influxdb:8086/g' /etc/grafana/provisioning/datasources/influxdb-emf-datasource.yml

ENTRYPOINT [ "wait-for-dependencies-postgres.sh" ]
CMD ["setup-grafana.sh"]
