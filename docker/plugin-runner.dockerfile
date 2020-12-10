FROM imlteam/python-service-base:6.3.0

CMD ["python", "./manage.py", "chroma_service", "--name=plugin_runner", "plugin_runner", "--console"]
