#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import json
import sys

f = open(sys.argv[1])

obj = json.load(f)

f.close()

servers = []
for server in obj["lustre_servers"]:
    servers.append(server["address"])

print "CHROMA_MANAGER=\"%s\"" % obj["chroma_managers"][0]["address"]
print "STORAGE_APPLIANCES=\"%s\"" % " ".join(servers)
print "CLIENT_1=\"%s\"" % obj["lustre_clients"].keys()[0]
