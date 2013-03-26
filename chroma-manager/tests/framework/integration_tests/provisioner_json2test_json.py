#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================

# A script that handles translating our json input into the format
# accepted by our vm provisioner.
#
# python provisioner_json2test_json.py input_file.json output_file.json


import json
import sys

provisioner_json_file = open(sys.argv[1])
config = json.load(provisioner_json_file)
provisioner_json_file.close()

if config.get('chroma_managers') and config.get('simulator'):
    for manager in config['chroma_managers']:
        manager['server_http_url'] = "%s:8000/" % manager['server_http_url']

if config.get('lustre_clients'):
    # Convert 'dict' style lustre_clients to a list of dicts.
    new_clients = {}
    for client in config['lustre_clients']:
        client_address = client['address']
        new_clients[client_address] = client
    config['lustre_clients'] = new_clients

test_json_file = open(sys.argv[2], 'w')
json.dump(config, test_json_file, sort_keys=True, indent=4)
test_json_file.close()
