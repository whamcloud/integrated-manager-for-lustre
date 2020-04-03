FROM imlteam/python-service-base:6.1.0-dev

CMD ["gunicorn", "wsgi:application", "-c", "./wsgi.py"]
