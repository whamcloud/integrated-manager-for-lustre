FROM imlteam/manager-service-base:5.1

RUN python setup.py install

COPY setup.sh /usr/local/bin/
ENTRYPOINT [ "setup.sh" ]