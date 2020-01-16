#! /bin/sh

# Remove the whitelist from the config file
sed -i '/^whitelist/d' /etc/grafana/grafana.ini \
  && /usr/share/grafana/setup-grafana \
  && /run.sh