FROM imlteam/python-service-base:6.3.0

CMD ["python", "./manage.py", "chroma_service", "--name=job_scheduler", "job_scheduler", "--console"]
