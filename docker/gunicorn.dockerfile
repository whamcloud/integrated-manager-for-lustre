FROM imlteam/python-service-base:6.3.0

CMD ["gunicorn", "wsgi:application", "-c", "./wsgi.py"]
