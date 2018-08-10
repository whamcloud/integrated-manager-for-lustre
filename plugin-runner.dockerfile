FROM imlteam/manager-service-base:extract-nginx

CMD ["python", "./manage.py", "chroma_service", "--name=plugin_runner", "plugin_runner", "--console"]