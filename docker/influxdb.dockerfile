FROM influxdb:1.7.6-alpine
USER root
COPY docker/influxdb/setup-influxdb /usr/local/bin
COPY docker/influxdb/setup-influxdb.sh /usr/local/bin

RUN apk add curl python
ENTRYPOINT ["setup-influxdb.sh"]
