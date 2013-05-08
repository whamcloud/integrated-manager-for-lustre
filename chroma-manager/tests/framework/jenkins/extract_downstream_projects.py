#
# Simple script to accept the jenkins json api output of $BUILD_URL/api/json?tree=runs[fingerprint[usage[name,ranges[ranges[end]]]]]
# and return the name and build number for each job triggered downstream of the original build in BUILD_URL.
#
# Usage: ./chroma_log_collection.py path/to/api_output.json

import json
import sys


if __name__ == '__main__':

    json_path = sys.argv[1]
    json_file = open(sys.argv[1])
    api_results = json.loads(json_file.read())

    builds = {}
    for run in api_results['runs']:
        fingerprints = run['fingerprint']
        for fingerprint in fingerprints:
            usage = fingerprint['usage']
            for use in usage:
                job_name = use['name']
                build_nums = []
                for k, ranges in use['ranges'].iteritems():
                    for range in ranges:
                        build_nums.append(range['end'] - 1)
                if job_name in builds:
                    build_nums.append(builds[job_name])
                latest_build_num = max(build_nums)
                builds[job_name] = latest_build_num

    builds_str = ''
    for job_name, build_num in builds.iteritems():
        build_substr = "%s,%s " % (job_name, build_num)
        builds_str = builds_str + build_substr
    print builds_str
