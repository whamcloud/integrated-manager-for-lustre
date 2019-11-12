FROM local/manager-service-base

CMD ["python", "./manage.py", "chroma_service", "--name=job_scheduler", "job_scheduler", "--console"]