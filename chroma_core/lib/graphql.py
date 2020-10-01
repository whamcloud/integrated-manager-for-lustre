import os
import sys
import requests
import settings
from django.db import connection

# this is a pointer to the module object instance itself.
this = sys.modules[__name__]
this.API_CRED = None

def get_api_session_request():
    if not this.API_CRED:
        cursor = connection.cursor()
        cursor.execute("SELECT * from api_key()")
        this.API_CRED = cursor.fetchone()
        cursor.close()
    s = requests.Session()
    s.headers.update({"AUTHORIZATION": "ApiKey {}:{}".format(this.API_CRED[0], this.API_CRED[1])})
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
