FROM python:2.7
WORKDIR /usr/share/chroma-manager/
COPY . .
RUN pip install -r requirements.txt