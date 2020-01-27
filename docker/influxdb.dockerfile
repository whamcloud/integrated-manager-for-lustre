FROM influxdb:1.7.6-alpine
USER root
RUN apk add curl

COPY docker/influxdb/setup-influxdb.sh /docker-entrypoint-initdb.d/
COPY docker/wait-for-dependencies.sh /usr/bin/

ENTRYPOINT ["wait-for-dependencies.sh"]
CMD ["/entrypoint.sh", "influxd"]
