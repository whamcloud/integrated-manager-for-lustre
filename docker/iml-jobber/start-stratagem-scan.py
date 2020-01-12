#!/usr/bin/env python

import requests
import sys, getopt

# Usage:
# start-stratagem-scan filesystem_id [report_duration [[purge_duration]]

args = sys.argv[1:]
short_opts = "f:r:p:"
long_opts = ["filesystem=", "report_duration=", "purge_duration="]

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
    elif opt in ("-r", "--report_duration"):
        report_duration = val
    elif opt in ("-p", "--purge_duration"):
        purge_duration = val

post_data = {"filesystem": filesystem, "report_duration": report_duration, "purge_duration": purge_duration}
s = requests.Session()
r = requests.get("https://nginx:7443/api/session/", verify=False)
s.headers.update({"X-CSRFToken": r.cookies["csrftoken"]})
s.cookies.set("csrftoken", r.cookies["csrftoken"])
s.post("https://nginx:7443/api/run_stratagem/", json=post_data, verify=False)
