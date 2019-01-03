import json
import sys
import os
import requests
from requests import adapters
from urlparse import urljoin, urlparse


from testconfig import config
from tests.utils.check_server_host import check_nodes_status


class HttpRequests(object):
    try:
        requests.packages.urllib3.disable_warnings()
    except AttributeError:
        # Running on OSX the disable_warnings is not available, so catch and deal with that. The effect of
        # ignoring the error is additional warnings so no real risk.
        pass

    def __init__(self, server_http_url="", *args, **kwargs):
        self.server_http_url = server_http_url
        self.session = requests.session()
        self.session.headers = {"Accept": "application/json", "Content-type": "application/json"}
        self.session.verify = False

        # Increase the number of pool connections so we can test large numbers
        # of connections to the api.
        adapter = adapters.HTTPAdapter(pool_connections=2000, pool_maxsize=2000)
        self.session.mount("http://", adapter)

    def _action(self, callable, url, **kwargs):
        try:
            return HttpResponse(callable(urljoin(self.server_http_url, url), **kwargs))
        except requests.ConnectionError as e:
            check_nodes_status(config)

            raise e

    def _send_action(self, callable, url, body, **kwargs):
        if body and "data" not in kwargs:
            kwargs["data"] = json.dumps(body)

        return self._action(callable, url, **kwargs)

    def get(self, url, **kwargs):
        if "data" in kwargs:
            kwargs["params"] = kwargs["data"]
            del kwargs["data"]

        return self._action(self.session.get, url, **kwargs)

    def post(self, url, body=None, **kwargs):
        return self._send_action(self.session.post, url, body, **kwargs)

    def put(self, url, body=None, **kwargs):
        return self._send_action(self.session.put, url, body, **kwargs)

    def patch(self, url, body=None, **kwargs):
        return self._send_action(self.session.patch, url, body, **kwargs)

    def delete(self, url, **kwargs):
        return self._action(self.session.delete, url, **kwargs)


# FIXME: in python-requests >= 1.0.x this class is redundant
# (the standard repsonse has .json and .ok)
class HttpResponse(requests.Response):
    def __init__(self, response, *args, **kwargs):
        super(HttpResponse, self).__init__(*args, **kwargs)
        self.__dict__.update(response.__dict__.copy())

    @property
    def json(self):
        if self.text == "[]":
            return []
        else:
            try:
                return json.loads(self.text)
            except ValueError:
                print("Bad JSON: %s" % self.text)
                raise

    @property
    def successful(self):
        # TODO: Make better
        return 200 <= self.status_code < 300


class AuthorizedHttpRequests(HttpRequests):
    def __init__(self, username, password, *args, **kwargs):
        super(AuthorizedHttpRequests, self).__init__(*args, **kwargs)

        # Set IGNORE_PROXY_LIST to either "all" or a space-separated list
        # of proxies to ignore when making requests.
        if "IGNORE_PROXY_LIST" in os.environ:
            ignore_set = set(os.environ["IGNORE_PROXY_LIST"].split())
            if len(ignore_set & set(["all", "ALL"])):
                for key in [key for key in os.environ.keys() if key in [key for p in ["_proxy", "_PROXY"] if p in key]]:
                    del (os.environ[key])
            else:
                for key in set(os.environ.keys()) & ignore_set:
                    del (os.environ[key])

        # Usually on our Intel laptops https_proxy is set, and needs to be unset for tests,
        # but let's not completely rule out the possibility that someone might want to run
        # the tests on a remote system using a proxy.
        if "https_proxy" in os.environ:
            manager_server = urlparse(self.server_http_url).netloc
            if ":" in manager_server:
                (manager_server, port) = manager_server.split(":")

            no_proxy = os.environ.get("no_proxy", "").split(",")
            will_proxy = True
            for item in no_proxy:
                if manager_server.endswith(item):
                    will_proxy = False
                    break

            if will_proxy:
                sys.stderr.write(
                    "Warning: Environment has https_proxy=%s set.  "
                    "Unless you really do want to use that proxy to "
                    "communicate with the manager at %s please ensure that "
                    "the no_proxy environment variable includes "
                    "%s (or a subdomain of it) in it\n"
                    % (os.environ["https_proxy"], self.server_http_url, manager_server)
                )

        response = self.get("/api/session/")
        if not response.successful:
            if "https_proxy" in os.environ:
                raise RuntimeError("Failed to open session (using proxy %s)" % (os.environ["https_proxy"]))
            else:
                raise RuntimeError("Failed to open session")
        self.session.headers["X-CSRFToken"] = response.cookies["csrftoken"]
        self.session.cookies["csrftoken"] = response.cookies["csrftoken"]
        self.session.cookies["sessionid"] = response.cookies["sessionid"]

        response = self.post("/api/session/", data=json.dumps({"username": username, "password": password}))
        if not response.successful:
            raise RuntimeError("Failed to authenticate with username: %s and password: %s" % (username, password))
