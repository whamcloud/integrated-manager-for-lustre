FROM imlteam/manager-service-base:extract-nginx:extract-nginx

CMD ["gunicorn", "chroma-manager:application", "-c", "./chroma-manager.py", "-e", "USE_CONSOLE=1", "--preload"]
