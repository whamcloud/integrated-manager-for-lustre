FROM base

COPY wait-for-settings.sh /usr/local/bin/
ENTRYPOINT [ "wait-for-settings.sh" ]

CMD ["python", "./manage.py", "chroma_service", "--name=corosync", "corosync", "--console"]