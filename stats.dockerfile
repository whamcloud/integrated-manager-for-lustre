FROM imlteam/manager-service-base:extract-nginx

CMD ["python", "./manage.py", "chroma_service", "--name=stats", "stats", "--console"]