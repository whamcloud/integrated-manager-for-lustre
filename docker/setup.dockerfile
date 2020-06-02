FROM imlteam/python-service-base:6.2.0-dev

RUN python setup.py install

COPY setup.sh /usr/local/bin/
ENTRYPOINT [ "setup.sh" ]
