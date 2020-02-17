FROM imlteam/python-service-base:5.1.1-dev

CMD ["python", "./manage.py", "chroma_service", "--name=http_agent", "http_agent", "--gevent", "--console"]