FROM imlteam/manager-service-base:5.1.1-dev

CMD ["python", "./manage.py", "chroma_service", "--name=plugin_runner", "plugin_runner", "--console"]