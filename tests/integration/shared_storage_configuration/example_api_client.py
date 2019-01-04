import os
import requests
import json
from urlparse import urljoin

LOCAL_CA_FILE = "chroma.ca"


def setup_ca(url):
    """
    To verify the server's identity on subsequent connections, first
    download the manager server's local CA.
    """

    if os.path.exists(LOCAL_CA_FILE):
        os.unlink(LOCAL_CA_FILE)

    response = requests.get(urljoin(url, "certificate/"), verify=False)
    if response.status_code != 200:
        raise RuntimeError("Failed to download CA: %s" % response.status_code)

    open(LOCAL_CA_FILE, "w").write(response.content)
    print("dir %s" % os.getcwd())
    print("Stored chroma CA certificate at %s" % LOCAL_CA_FILE)


def list_hosts(url, username, password):
    # Create a local session context
    session = requests.session()
    session.headers = {"Accept": "application/json", "Content-type": "application/json"}
    session.verify = LOCAL_CA_FILE

    # Obtain a session ID from the API
    response = session.get(urljoin(url, "api/session/"))
    if not 200 <= response.status_code < 300:
        raise RuntimeError("Failed to open session")
    session.headers["X-CSRFToken"] = response.cookies["csrftoken"]
    session.cookies["csrftoken"] = response.cookies["csrftoken"]
    session.cookies["sessionid"] = response.cookies["sessionid"]

    # Authenticate our session by username and password
    response = session.post(urljoin(url, "api/session/"), data=json.dumps({"username": username, "password": password}))
    if not 200 <= response.status_code < 300:
        raise RuntimeError("Failed to authenticate")

    # Get a list of servers
    response = session.get(urljoin(url, "api/host/"))
    if not 200 <= response.status_code < 300:
        raise RuntimeError("Failed to get host list")
    body_data = json.loads(response.text)
    # Print out each host's address
    return [host["fqdn"] for host in body_data["objects"]]


if __name__ == "__main__":
    url = "https://localhost:8000/"
    username = "debug"
    password = "password"
    setup_ca(url)
    print(list_hosts(url, username, password))
