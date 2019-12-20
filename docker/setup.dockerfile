FROM imlteam/manager-service-base:5.1

RUN yum install python-setuptools \
  && python setup.py install

COPY setup.sh /usr/local/bin/
ENTRYPOINT [ "setup.sh" ]