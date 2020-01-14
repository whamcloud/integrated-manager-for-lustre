FROM imlteam/manager-service-base:dev

CMD ["python", "./manage.py", "chroma_service", "--name=corosync", "corosync", "--console"]