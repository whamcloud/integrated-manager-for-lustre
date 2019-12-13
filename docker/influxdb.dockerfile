FROM influxdb/influxdb:1.7.6-alpine
USER root
COPY docker/influx/setup-influxdb /usr/local/bin
COPY docker/influx/setup-influxdb.sh /usr/local/bin

RUN apk add curl python
ENTRYPOINT ["wait-for-dependencies.sh"]
CMD ["setup-influxdb.sh"]