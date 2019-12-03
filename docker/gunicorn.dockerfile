FROM imlteam/manager-service-base:5.1

CMD ["gunicorn", "wsgi:application", "-c", "./wsgi.py"]
