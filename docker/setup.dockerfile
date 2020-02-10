FROM imlteam/manager-service-base:5.1.1-dev

RUN python setup.py install

COPY setup.sh /usr/local/bin/
ENTRYPOINT [ "setup.sh" ]
