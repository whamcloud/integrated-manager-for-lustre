#
# Simple script to accept the jenkins json api output of $BUILD_URL/api/json?tree=runs[fingerprint[usage[name,ranges[ranges[end]]]]]
# and return the name and build number for each job triggered downstream of the original build in BUILD_URL.
#
# Usage: ./aggregate_test_results.py jenkins_url username password build_job_name build_job_build_number valid_test_jobs required_tests

import errno
import os
import re
import sys
from jenkinsapi.utils.requester import Requester

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
    valid_test_jobs = set(sys.argv[6].split())
    required_tests = set(sys.argv[7].split())

    # Fetch the downstream build info from jenkins
    req = Requester(username, password, baseurl=jenkins_url, ssl_verify=False)
    jenkins = api.Jenkins(jenkins_url, username=username, password=password, requester=req)
    assert jenkins.get_jobs_list()  # A test we are logged in
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
                    job_name = use['name'].split('/')[0]
                    if job_name in downstream_jobs_names and job_name in valid_test_jobs:
                        build_nums = []
                        for k, ranges in use['ranges'].iteritems():
                            for range in ranges:
                                build_nums.append(range['end'] - 1)
                        latest_build = max(build_nums)
                        try:
                            if job_name == use['name']:
                                # Job is not multiconfiguration
                                test_runs.append(jenkins.get_job(job_name).get_build(latest_build))
                            else:
                                # Job is multiconfiguration
                                master_job = jenkins.get_job(job_name)
                                master_build = master_job.get_build(latest_build)
                                for run in master_build.get_matrix_runs():
                                    test_runs.append(run)
                            logging.info("Added '%s' build num '%s' to the list of test runs" % (job_name, latest_build))
                        except Exception, e:
                            # Can happen for things like old disabled jobs.
                            # Any real missing builds will be caught by the
                            # check for required runs below.
                            logging.warning("Exception trying to get '%s' build num '%s': '%s'" % (job_name, latest_build, e))
                            raise e

    # Double check all jobs have finished running
    for test_run in test_runs:
        test_run.block_until_complete()

    # Gather test and coverage reports from test jobs
    mkdir_p('coverage_files')
    mkdir_p('test_reports')
    mkdir_p('linking_artifacts')

    for test_run in test_runs:
        artifacts = test_run.get_artifact_dict()

        if '.coverage' in artifacts:
            coverage_report = artifacts['.coverage']
            coverage_report.save('coverage_files/.coverage.%s' % test_run.job.name)

        test_reports = [v for k, v in artifacts.iteritems() if re.match(".*test.*.xml", k)]
        logging.info("Found the following reports for %s: '%s'" % (test_run.name, [r.filename for r in test_reports]))
        mkdir_p("test_reports/%s" % os.path.normpath(test_run.name))
        for test_report in test_reports:
            test_report.save_to_dir("test_reports/%s/" % os.path.normpath(test_run.name))

        # Also download the test_info.txt for each so we still get a link even if no
        # report was generated in the run.
        if 'test_info.txt' in artifacts:
            artifacts['test_info.txt'].save('linking_artifacts/%s_test_info.txt' % test_run.name)

    # Ensure all of the jobs required to be run to land are passing
    logging.info("Requiring these tests: '%s'" % required_tests)
    found_tests = set([t.job.name for t in test_runs if os.listdir("test_reports/%s" % t.name)])
    logging.info("Found these tests: '%s'" % found_tests)
    missing_tests = required_tests.difference(found_tests)
    if missing_tests:
        print "MISSING TEST RESULTS! Did not find an expected test report for these tests: '%s'." % ', '.join(missing_tests)
        exit(1)

    # Check if there were test failures
    passing_tests = [t for t in test_runs if t.is_good()]
    if len(passing_tests) == len(test_runs):
        print "SUCCESS"
    else:
        print "FAILED"
