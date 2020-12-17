FROM python:3.9

RUN apt-get update
RUN pip install --upgrade pip

COPY entrypoint.py /entrypoint.py
COPY requirements.txt requirements.txt

RUN chmod +x /entrypoint.py

WORKDIR /

RUN pip install -r requirements.txt

ENTRYPOINT ["/entrypoint.py"]