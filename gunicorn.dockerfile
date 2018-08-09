FROM imlteam/manager-service-base

CMD ["gunicorn", "chroma-manager:application", "-c", "./chroma-manager.py", "--preload"]
