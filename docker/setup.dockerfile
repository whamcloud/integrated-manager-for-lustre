FROM imlteam/python-service-base:6.3.0

RUN python2 setup.py install

COPY setup.sh /usr/local/bin/
ENTRYPOINT [ "setup.sh" ]
