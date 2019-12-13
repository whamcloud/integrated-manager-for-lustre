FROM grafana/grafana
USER root
COPY docker/grafana/setup-grafana /usr/share/grafana/
COPY docker/grafana/setup-grafana.sh /usr/local/bin/
COPY docker/grafana/grafana.ini /etc/grafana/
COPY docker/grafana/provisioning/dashboards/* /etc/grafana/provisioning/dashboards/
COPY docker/wait-for-dependencies-postgres.sh /usr/bin/

RUN apk add postgresql-client curl python
ENTRYPOINT [ "wait-for-dependencies-postgres.sh" ]
CMD ["setup-grafana.sh"]
