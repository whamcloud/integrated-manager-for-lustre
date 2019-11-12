FROM local/manager-service-base

CMD ["python", "./manage.py", "chroma_service", "--name=http_agent", "http_agent", "--gevent", "--console"]