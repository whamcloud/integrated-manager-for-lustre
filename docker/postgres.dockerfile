FROM postgres:9.6.17-alpine

COPY docker/postgres/enable_btree_gist.sh /docker-entrypoint-initdb.d/
