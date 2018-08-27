FROM imlteam/manager-service-base

CMD ["python", "./manage.py", "chroma_service", "--name=stats", "stats", "--console"]