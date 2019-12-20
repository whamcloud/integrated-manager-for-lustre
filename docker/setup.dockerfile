FROM imlteam/manager-service-base:dev

RUN python setup.py install

COPY setup.sh /usr/local/bin/
ENTRYPOINT [ "setup.sh" ]
