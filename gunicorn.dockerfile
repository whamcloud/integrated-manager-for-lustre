FROM imlteam/manager-service-base

ENTRYPOINT ["gunicorn", "chroma-manager:application", "-c", "./chroma-manager.py", "--preload"]
