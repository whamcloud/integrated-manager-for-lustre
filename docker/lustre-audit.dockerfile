FROM imlteam/manager-service-base:dev

CMD ["python", "./manage.py", "chroma_service", "--name=lustre_audit", "lustre_audit", "--console"]