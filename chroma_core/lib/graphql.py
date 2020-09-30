import json
import os
import requests
import settings
from django.db import connection


API_USER = None
API_KEY = None


def get_api_session_request():
    if not API_USER or not API_KEY:
        cursor = connection.cursor()
        cursor.execute("SELECT * from api_key()")
        (API_USER, API_KEY) = cursor.fetchone()
        cursor.close()
    s = requests.Session()
    s.headers.update({"AUTHORIZATION": "ApiKey {}:{}".format(API_USER, API_KEY)})
    return s


def graphql_query(query):
    """
    Issue a GraphQL query
    """
    s = get_api_session_request()
    path = os.path.join(settings.IML_API_PROXY_PASS, "graphql")
    q = {"query": query}
    res = s.post(url=path, json=q)

    return res.json()["data"]
