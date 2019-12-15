FROM influxdb:1.7.6-alpine
USER root
COPY docker/influxdb/influxdb.conf /etc/influxdb/
COPY docker/influxdb/setup-influxdb /usr/local/bin/
COPY docker/influxdb/setup-influxdb.sh /docker-entrypoint-initdb.d/

RUN apk add curl python
ENTRYPOINT ["/entrypoint.sh"]
CMD ["influxd"]
