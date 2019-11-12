FROM local/manager-service-base

CMD ["python", "./manage.py", "chroma_service", "--name=syslog", "syslog", "--console"]