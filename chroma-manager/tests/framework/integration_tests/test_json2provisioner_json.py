#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================

# A script that handles translating our json input into the format
# accepted by our vm provisioner.
#
# python test_json2provisioner_json.py input_file.json output_file.json


import json
import sys

test_json_file = open(sys.argv[1])
config = json.load(test_json_file)
test_json_file.close()

if config.get('lustre_clients'):
    # Convert 'dict' style lustre_clients to a list of dicts.
    new_clients = []
    for client_address, client_attributes in config['lustre_clients'].items():
        new_client = {
            "address": client_address
        }
        for key, value in client_attributes.items():
            new_client[key] = value
        new_clients.append(new_client)
    config['lustre_clients'] = new_clients

provisioner_json_file = open(sys.argv[2], 'w')
json.dump(config, provisioner_json_file, sort_keys=True, indent=4)
provisioner_json_file.close()
