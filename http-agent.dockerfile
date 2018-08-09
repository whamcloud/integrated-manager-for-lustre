FROM imlteam/manager-service-base:extract-nginx

COPY wait-for-settings.sh /usr/local/bin/
ENTRYPOINT [ "wait-for-settings.sh" ]

CMD ["python", "./manage.py", "chroma_service", "--name=http_agent", "http_agent", "--gevent", "--console"]