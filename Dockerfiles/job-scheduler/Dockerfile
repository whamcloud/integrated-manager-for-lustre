FROM base
COPY . .

COPY wait-for-settings.sh /usr/local/bin/
ENTRYPOINT [ "wait-for-settings.sh" ]

CMD ["python", "./manage.py", "chroma_service", "--name=job_scheduler", "job_scheduler"]