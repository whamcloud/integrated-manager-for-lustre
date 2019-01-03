# A script that handles translating our json input into the format
# accepted by our vm provisioner.
#
# python test_json2provisioner_json.py input_file.json output_file.json


import json
import sys
import os

test_json_file = open(sys.argv[1])
config = json.load(test_json_file)
test_json_file.close()

# insert the jenkins metadata if not done by the caller already
if config.get("repos", False):
    if config["repos"]["chroma"]["build_job"] == "BUILD_JOB_NAME":
        config["repos"]["chroma"]["build_job"] = os.environ["BUILD_JOB_NAME"]
    if config["repos"]["chroma"]["build_number"] == "BUILD_JOB_BUILD_NUMBER":
        config["repos"]["chroma"]["build_number"] = int(os.environ["BUILD_JOB_BUILD_NUMBER"])

provisioner_json_file = open(sys.argv[2], "w")
json.dump(config, provisioner_json_file, sort_keys=True, indent=4)
provisioner_json_file.close()
