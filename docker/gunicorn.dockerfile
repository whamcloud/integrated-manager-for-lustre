FROM imlteam/manager-service-base:5.1.1-dev

CMD ["gunicorn", "wsgi:application", "-c", "./wsgi.py"]
