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
COPY --from=rust-emf-gui /usr/share/emf-manager/rust-emf-gui /usr/share/emf-manager/rust-emf-gui
COPY --from=imlteam/online-help:6.1 /root /usr/lib/emf-manager/emf-online-help
COPY --from=builder /build/emf.template /etc/nginx/conf.d/emf.template
CMD dockerize -template /etc/nginx/conf.d/emf.template:/etc/nginx/conf.d/default.conf -stdout /var/log/nginx/access.log -stderr /var/log/nginx/error.log -wait file:///var/lib/chroma/emf-settings.conf -timeout 10m nginx
