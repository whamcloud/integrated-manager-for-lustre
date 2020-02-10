FROM imlteam/python-service-base:5.1.1-dev

CMD ["python", "./manage.py", "chroma_service", "--name=lustre_audit", "lustre_audit", "--console"]