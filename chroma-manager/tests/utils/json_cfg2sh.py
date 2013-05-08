import json
import sys

f = open(sys.argv[1])

obj = json.load(f)

f.close()

servers = []
for server in obj["lustre_servers"]:
    servers.append(server["address"])

print "CHROMA_MANAGER=\"%s\"" % obj["chroma_managers"][0]["address"]
print "STORAGE_APPLIANCES=(%s)" % " ".join(servers)
print "CLIENT_1=\"%s\"" % obj["lustre_clients"].keys()[0] if obj.get('lustre_clients') else ""
print "TEST_RUNNER=\"%s\"" % obj["test_runners"][0]['address'] if obj.get("test_runners") else ""
print "HOST_IP=\"%s\"" % obj["hosts"].values()[0]['ip_address']  # This will have to change in case cluster has multiple hosts for VMs, but an adequate placeholder for this version of the prototype.
