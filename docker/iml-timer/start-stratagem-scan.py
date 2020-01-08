#!/usr/bin/env python

# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import requests
import os, sys, getopt

args = sys.argv[1:]
short_opts = "f:r:p:"
long_opts = ["filesystem=", "report=", "purge="]

url = os.getenv("SERVER_HTTP_URL")
api_user = os.getenv("API_USER")
api_key = os.getenv("API_KEY")

try:
    arguments, values = getopt.getopt(args, short_opts, long_opts)
except getopt.error as err:
    print(str(err))
    sys.exit(2)

report_duration = None
purge_duration = None
for opt, val in arguments:
    if opt in ("-f", "--filesystem"):
        filesystem = val
    elif opt in ("-r", "--report"):
        report_duration = val
    elif opt in ("-p", "--purge"):
        purge_duration = val

post_data = {"filesystem": filesystem, "report_duration": report_duration, "purge_duration": purge_duration}
s = requests.Session()
s.headers.update({"AUTHORIZATION": "ApiKey {}:{}".format(api_user, api_key)})
response = s.post("{}/api/run_stratagem/".format(url), json=post_data, verify=False)

if not response.ok:
    raise Exception(response.reason)

