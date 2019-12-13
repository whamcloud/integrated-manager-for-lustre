FROM influxdb/influxdb:latest-alpine
USER root
COPY docker/influx/setup-influx /usr/local/bin
COPY docker/influx/setup-influx.sh /usr/local/bin

RUN apk add curl python
ENTRYPOINT ["wait-for-dependencies.sh"]
CMD ["setup-influx.sh"]