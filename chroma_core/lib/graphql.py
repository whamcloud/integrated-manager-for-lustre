import os
import sys
import requests
import settings
from django.db import connection

# this is a pointer to the module object instance itself.
this = sys.modules[__name__]
this.API_CRED = None


class GraphQlQueryException(Exception):
    pass


def get_api_session_request():
    if not this.API_CRED:
        cursor = connection.cursor()
        cursor.execute("SELECT * from api_key()")
        this.API_CRED = cursor.fetchone()
        cursor.close()

    s = requests.Session()
    s.headers.update({"AUTHORIZATION": "ApiKey {}:{}".format(this.API_CRED[0], this.API_CRED[1])})

    return s


def graphql_query(query, variables={}):
    """
    Issue a GraphQL query
    """
    s = get_api_session_request()
    path = os.path.join(settings.IML_API_PROXY_PASS, "graphql")
    q = {"query": query, "variables": variables}
    res = s.post(url=path, json=q)

    body = res.json()

    errors = body.get("errors")

    if errors is not None:
        raise GraphQlQueryException(errors)

    return body.get("data")


def get_targets(**kwargs):
    query = """
        query Targets($limit: Int, $offset: Int, $dir: SortDir, $fsname: String, $exclude_unmounted: Boolean) {
          targets(limit: $limit, offset: $offset, dir: $dir, fsName: $fsname, excludeUnmounted: $exclude_unmounted) {
            id
            state
            name
            dev_path: devPath
            active_host_id: activeHostId
            host_ids: hostIds
            filesystems
            uuid
            mount_path: mountPath
          }
        }
    """

    return graphql_query(query, variables=kwargs)["targets"]
