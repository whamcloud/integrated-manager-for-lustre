#!/bin/bash

gunzip /tmp/chromadb_*.sql.gz
chroma-config stop


cd /tmp && \
sudo -u postgres -- pg_dump -U chroma -F p -w -f other-db-bits.sql -t 'chroma_core_series' -t 'chroma_core_sample_*' -t 'chroma_core_logmessage'

sudo -u postgres -- dropdb chroma
sudo -u postgres -- createdb chroma

cd /tmp && \
sudo -u postgres -- psql chroma < chromadb_*.sql && \
sudo -u postgres -- psql chroma < other-db-bits.sql

chroma-config start
