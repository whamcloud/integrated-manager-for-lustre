FROM imlteam/manager-service-base:5.1

CMD ["python", "./manage.py", "chroma_service", "--name=job_scheduler", "job_scheduler", "--console"]