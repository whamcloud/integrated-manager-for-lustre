FROM imlteam/python-service-base:6.1.0-dev

CMD ["python", "./manage.py", "chroma_service", "--name=corosync", "corosync", "--console"]