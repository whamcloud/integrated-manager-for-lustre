import json
import sys

f = open(sys.argv[1])

obj = json.load(f)

f.close()

servers = []
for server in obj["lustre_servers"]:
    servers.append(server["address"])

all_nodes = [obj["chroma_managers"][0]["address"]] + servers

print "CHROMA_MANAGER=\"%s\"" % obj["chroma_managers"][0]["address"]
print "STORAGE_APPLIANCES=(%s)" % " ".join(servers)

if obj.get('lustre_clients'):
    print "CLIENT_1=\"%s\"" % obj["lustre_clients"].keys()[0]
    all_nodes.append(obj["lustre_clients"].keys()[0])

if obj.get("test_runners"):
    print "TEST_RUNNER=\"%s\"" % obj["test_runners"][0]['address']
    all_nodes.append(obj["test_runners"][0]['address'])

print "HOST_IP=\"%s\"" % obj["hosts"].values()[0]['ip_address']  # This will have to change in case cluster has multiple hosts for VMs, but an adequate placeholder for this version of the prototype.

print "ALL_NODES=\"%s\"" % " ".join(list(set(all_nodes)))

chroma_manager = obj["chroma_managers"][0]
user = chroma_manager["users"][0]
print "CHROMA_USER=\"%s\"" % user["username"]
print "CHROMA_PASS=\"%s\"" % user["password"]
if user.get("email"):
    print "CHROMA_EMAIL=\"%s\"" % user["email"]
if chroma_manager.get("ntp_server"):
    print "CHROMA_NTP_SERVER=\"%s\"" % chroma_manager["ntp_server"]
