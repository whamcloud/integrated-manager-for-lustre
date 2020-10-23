FROM imlteam/python-service-base:6.2.0

CMD ["gunicorn", "wsgi:application", "-c", "./wsgi.py"]
