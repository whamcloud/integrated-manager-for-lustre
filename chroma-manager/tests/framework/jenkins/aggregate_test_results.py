#
# Simple script to accept the jenkins json api output of $BUILD_URL/api/json?tree=runs[fingerprint[usage[name,ranges[ranges[end]]]]]
# and return the name and build number for each job triggered downstream of the original build in BUILD_URL.
#
# Usage: ./aggregate_test_results.py jenkins_url username password build_job_name build_job_build_number valid_test_jobs required_tests

import errno
import os
import re
import sys

from jenkinsapi import api

import logging
logging.basicConfig(filename="test_aggregation.log", level=logging.INFO)


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


if __name__ == '__main__':

    # Store the command line arguments
    jenkins_url = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    build_job_name = sys.argv[4]
    build_job_build_number = int(sys.argv[5])
    valid_test_jobs = sys.argv[6].split()
    required_tests = sys.argv[7].split()

    # Fetch the downstream build info from jenkins
    jenkins = api.Jenkins(jenkins_url, username=username, password=password)
    assert jenkins.login()
    job = jenkins.get_job(build_job_name)
    build = job.get_build(build_job_build_number)

    test_runs = []
    downstream_jobs_names = build.job.get_downstream_job_names()
    fingerprint_data = build.get_data("%s?depth=2&tree=runs[fingerprint[fileName,usage[name,ranges[ranges[end]]]]]" % build.python_api_url(build.baseurl))
    for run in fingerprint_data['runs']:
        fingerprints = run['fingerprint']
        for fingerprint in fingerprints:
            if fingerprint['fileName'] == 'build_info.txt':
                usage = fingerprint['usage']
                for use in usage:
                    if use['name'] in downstream_jobs_names and use['name'] in valid_test_jobs:
                        build_nums = []
                        for k, ranges in use['ranges'].iteritems():
                            for range in ranges:
                                build_nums.append(range['end'] - 1)
                        latest_build = max(build_nums)
                        try:
                            test_runs.append(jenkins.get_job(use['name']).get_build(latest_build))
                            logging.info("Added '%s' build num '%s' to the list of test runs" % (use['name'], latest_build))
                        except Exception, e:
                            # Can happen for things like old disabled jobs.
                            # Any real missing builds will be caught by the
                            # check for required runs below.
                            logging.warning("Exception trying to get '%s' build num '%s': '%s'" % (use['name'], latest_build, e))

    # Double check all jobs have finished running
    for test_run in test_runs:
        test_run.block_until_complete()

    # Gather test and coverage reports from test jobs
    mkdir_p('coverage_files')
    mkdir_p('test_reports')

    for test_run in test_runs:
        artifacts = test_run.get_artifact_dict()

        if '.coverage' in artifacts:
            coverage_report = artifacts['.coverage']
            coverage_report.save('coverage_files/.coverage.%s' % test_run.job.name)

        test_reports = [v for k, v in artifacts.iteritems() if re.match("test_reports/.*", k)]
        mkdir_p("test_reports/%s" % test_run.job.name)
        for test_report in test_reports:
            test_report.savetodir("test_reports/%s/" % test_run.job.name)

    # Ensure all of the jobs required to be run to land are passing
    logging.info("Requiring these tests: '%s'" % required_tests)
    found_tests = [t.job.name for t in test_runs]
    logging.info("Found these test runs: '%s'" % found_tests)
    for required_test in required_tests:
        if not required_test in found_tests:
            print "MISSING TEST RESULTS! Expected to see results from [%s] and only found results from [%s]." % (required_tests, found_tests)
            exit(1)

    # Check if there were test failures
    passing_tests = [t for t in test_runs if t.is_good()]
    if len(passing_tests) == len(test_runs):
        print "SUCCESS"
    else:
        print "FAILED"
