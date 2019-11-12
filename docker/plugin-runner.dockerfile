FROM local/manager-service-base

CMD ["python", "./manage.py", "chroma_service", "--name=plugin_runner", "plugin_runner", "--console"]