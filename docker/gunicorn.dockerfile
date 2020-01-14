FROM imlteam/manager-service-base:dev

CMD ["gunicorn", "wsgi:application", "-c", "./wsgi.py"]
