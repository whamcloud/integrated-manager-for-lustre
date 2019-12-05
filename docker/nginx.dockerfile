FROM python:2.7 as builder
WORKDIR /build
COPY chroma-manager.conf.template ./
COPY docker/setup-nginx ./
RUN ./setup-nginx

FROM nginx:alpine
ENV DOCKERIZE_VERSION v0.6.1
ENV HTTPS_FRONTEND_PORT 7443
RUN apk update && apk upgrade && \
  apk add --no-cache openssl  \
  && wget https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-alpine-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
  && tar -C /usr/local/bin -xzvf dockerize-alpine-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
  && rm dockerize-alpine-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
  && apk del gettext
COPY --from=imlteam/gui:5.1 /home/node/GUI /usr/lib/iml-manager/iml-gui
COPY --from=imlteam/online-help:5.1 /root /usr/lib/iml-manager/iml-online-help
COPY --from=imlteam/old-gui:5.1 /root /usr/lib/node_modules/@iml/old-gui
COPY --from=imlteam/socket-worker:5.1 /root /usr/lib/node_modules/@iml/socket-worker/targetdir
COPY --from=imlteam/iml-wasm-components:5.1 /usr/share/iml-manager/iml-wasm-components /usr/share/iml-manager/iml-wasm-components
COPY --from=builder /build/iml.template /etc/nginx/conf.d/iml.template
CMD dockerize -template /etc/nginx/conf.d/iml.template:/etc/nginx/conf.d/default.conf -stdout /var/log/nginx/access.log -stderr /var/log/nginx/error.log -wait file:///var/lib/chroma/iml-settings.conf -timeout 10m nginx