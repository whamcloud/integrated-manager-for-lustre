FROM base
COPY . .

COPY wait-for-settings.sh /usr/local/bin/
ENTRYPOINT [ "wait-for-settings.sh" ]

CMD ["gunicorn", "chroma-manager:application", "-c", "./chroma-manager.py", "--preload"]
