FROM imlteam/manager-service-base:5.1

CMD ["python", "./manage.py", "chroma_service", "--name=http_agent", "http_agent", "--gevent", "--console"]