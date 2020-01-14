FROM imlteam/manager-service-base:dev

CMD ["python", "./manage.py", "chroma_service", "--name=http_agent", "http_agent", "--gevent", "--console"]