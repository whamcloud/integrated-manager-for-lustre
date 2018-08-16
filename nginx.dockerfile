FROM nginx:alpine

ENV DOCKERIZE_VERSION v0.6.1

COPY chroma-manager.conf.template /tmp

RUN apk update && apk upgrade && \
    apk add --no-cache sed openssl  \
    && wget https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-alpine-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && tar -C /usr/local/bin -xzvf dockerize-alpine-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && rm dockerize-alpine-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && cat /tmp/chroma-manager.conf.template \
        | sed -E "s/\{\{(.*)}}/\{\{ \.Env\.\1 }}/g" \
        | sed -E 's/proxy_pass \{\{ \.Env\.(.*) }}.*;/set $proxy_upstream \{\{ \.Env\.\1 }};\n\        proxy_pass $proxy_upstream$uri$is_args$query_string;/g' \
        | sed -E '/proxy_read_timeout.+;/a\\n    resolver 127.0.0.11 ipv6=off valid=5s;\n\    resolver_timeout 5s;' \
        | sed -E '/location \/iml-device-aggregator \{/{N;N;N;N;s/$/\n        client_body_buffer_size 1m;\n\        client_max_body_size 8m;\n/}' \ 
        > /etc/nginx/conf.d/iml.template \
    && rm -rf /tmp/chroma-manager.conf.template \
    && apk del sed gettext

COPY --from=imlteam/gui /home/node/GUI /usr/lib/iml-manager/iml-gui
COPY --from=imlteam/online-help /root /usr/lib/iml-manager/iml-online-help
COPY --from=imlteam/old-gui /root /usr/lib/node_modules/@iml/old-gui
COPY --from=imlteam/socket-worker /root /usr/lib/node_modules/@iml/socket-worker/targetdir

CMD dockerize -template /etc/nginx/conf.d/iml.template:/etc/nginx/conf.d/default.conf -stdout /var/log/nginx/access.log -stderr /var/log/nginx/error.log -wait file:///var/lib/chroma/iml-settings.conf nginx