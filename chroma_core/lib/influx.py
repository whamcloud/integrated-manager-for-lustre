import requests
import settings


def post(db, query):
    requests.post(
        "{}/query".format(settings.INFLUXDB_PROXY_PASS),
        params={
            "db": db,
            "q": query,
        },
    )


def get(db, query):
    requests.get(
        "{}/query".format(settings.INFLUXDB_PROXY_PASS),
        params={
            "db": db,
            "q": query,
        },
    )
