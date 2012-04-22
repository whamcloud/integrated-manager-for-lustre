#!/usr/bin/env python
#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import requests
import json

url = "http://localhost:8000/api"

# Establish a session
session = requests.session(headers = {"Accept": "application/json", "Content-type": "application/json"})
response = session.get("%s/session/" % url)
if not 200 <= response.status_code < 300:
    raise RuntimeError("Failed to open session")
session.headers['X-CSRFToken'] = response.cookies['csrftoken']
session.cookies['csrftoken'] = response.cookies['csrftoken']
session.cookies['sessionid'] = response.cookies['sessionid']

# Log in
username = 'debug'
password = 'password'
response = session.post("%s/session/" % url, data = json.dumps({'username': username, 'password': password}))
if not 200 <= response.status_code < 300:
    raise RuntimeError("Failed to authenticate")

# Get a list of servers
response = session.get("%s/host/" % url)
if not 200 <= response.status_code < 300:
    raise RuntimeError("Failed to get host list")
body_data = json.loads(response.text)
# Print out each host's address
print [host['address'] for host in body_data['objects']]
