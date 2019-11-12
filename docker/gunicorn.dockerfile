FROM local/manager-service-base

CMD ["gunicorn", "wsgi:application", "-c", "./wsgi.py"]
