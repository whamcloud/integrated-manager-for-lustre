FROM influxdb:1.8.0-alpine
USER root
RUN apk add curl

COPY docker/influxdb/setup-influxdb.sh /docker-entrypoint-initdb.d/
COPY docker/wait-for-settings.sh /usr/bin/

ENTRYPOINT ["wait-for-settings.sh"]
CMD ["/entrypoint.sh", "influxd"]
