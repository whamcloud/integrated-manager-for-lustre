FROM influxdb:1.7.6-alpine
USER root
COPY docker/influxdb/influxdb.conf /etc/influxdb/
COPY docker/influxdb/setup-influxdb /usr/local/bin/
COPY docker/influxdb/setup-influxdb.sh /docker-entrypoint-initdb.d/
COPY docker/wait-for-dependencies.sh /usr/local/bin/

RUN apk add curl python
ENTRYPOINT ["wait-for-dependencies.sh"]
CMD ["/entrypoint.sh", "influxd", "-config", "/etc/influxdb/influxdb.conf"]
