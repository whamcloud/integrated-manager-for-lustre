FROM imlteam/manager-service-base:extract-nginx

CMD ["python", "./manage.py", "chroma_service", "--name=corosync", "corosync", "--console"]