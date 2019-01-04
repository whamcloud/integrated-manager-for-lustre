#
# Simple script to accept the jenkins json api output of $BUILD_URL/api/json?tree=runs[fingerprint[usage[name,ranges[ranges[end]]]]]
# and return the name and build number for each job triggered downstream of the original build in BUILD_URL.
#
# Usage: ./aggregate_test_results.py jenkins_url build_job_name build_job_build_number valid_test_jobs required_tests

from collections import defaultdict
import errno
import os
import re
import sys

from jenkinsapi.utils.requester import Requester
from jenkinsapi import api

import logging

logging.basicConfig(filename="test_aggregation.log", level=logging.INFO)

import requests

requests.packages.urllib3.disable_warnings()


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def compile_unique_runs(usages):
    """
    Take the usage data from Jenkins, and convert it into a dict of test suites
    mapped to the runs of that suite for this build.

    Usage data is a record from Jenkins of which jobs used a given fingerprint.
    Fingerprints are how our test jobs and their associated builds are linked
    in Jenkins. So it is from this data we must dig out which test runs are for
    our build. Please see the jenkins api docs for details on the exact formats
    of usages and fingerprints.

    :param usages: A list of usage data from the fingerprints for a build job.

    :returns: A dict where they keys are the test suite names, and the value is
        the list of build numbers of that test suite that the usages data
        indicated were downstream of our build job.
    """
    runs = {}
    for usage in usages:
        for use in usage:
            # Get the pure job name, minus any extra stuff about the distro, etc.
            job_name = use["name"].split("/")[0]

            # Use the ranges of build numbers provided in the usage and
            # extrapolate out into a complete list of each number in the range,
            # each of which is a test run in Jenkins associated with our build.
            build_nums = []
            for ranges in use["ranges"].values():
                for single_range in ranges:
                    build_nums.extend(range(single_range["start"], single_range["end"]))

            # The complete set of fingerprints will end up giving references to
            # the same build numbers multiple times. So we keep it to a unique
            # set so we don't waste time re-evaluating the same runs over and
            # over again with costly calls to Jenkins.
            runs[job_name] = list(set(runs.get(job_name, []) + build_nums))

    for job_name, unique_build_nums in runs.iteritems():
        logging.info("Found these build numbers for '%s': '%s'" % (job_name, unique_build_nums))

    return runs


def get_best_runs(job_name, build_nums):
    """
    Return the most recent passing run for each distro, or, if none have passed,
    the most recent non-passing run.

    :param job_name: The name of the test suite in Jenkins, eg, chroma-unit-tests.
    :param build_nums: The build numbers in Jenkins for that test runs of that suite
        that we want to find the best run of.

    :return: List of the best builds to use in the reporting from this test suite.
    """
    # Get the build object from jenkins for each run
    test_runs = defaultdict(list)
    for build_num in build_nums:
        master_job = jenkins.get_job(job_name)
        try:
            master_build = master_job.get_build(build_num)
        except KeyError:
            # Tests that are still running or have fallen out of history will have a KeyError
            continue

        for run in master_build.get_matrix_runs():
            try:
                distro = re.search("distro=(.*?),", run.baseurl).group(1)
            except:
                distro = re.search("slave=(.*?)%", run.baseurl).group(1)
            test_runs[distro].append(run)

    # Pick out the most recent passing build if one exists, else the most recent non-passing
    best_runs = []
    for distro, runs in test_runs.iteritems():
        most_recent_pass = None
        most_recent_fail = None

        # By first sorting the runs by build number, we ensure that we have the
        # most recent for each at the end.
        for run in sorted(runs, key=lambda item: item.buildno):
            if run.is_good():
                most_recent_pass = run
            else:
                most_recent_fail = run

        best_run = most_recent_pass if most_recent_pass else most_recent_fail
        logging.info(
            "Selected build num '%s' as the best run for '%s' distro '%s'" % (best_run.buildno, job_name, distro)
        )
        best_runs.append(best_run)

    return best_runs


if __name__ == "__main__":

    # Store the command line arguments
    jenkins_url = sys.argv[1]
    build_job_name = sys.argv[2]
    build_job_build_number = int(sys.argv[3])
    valid_test_jobs = set(sys.argv[4].split())
    required_tests = set(sys.argv[5].split())

    # Fetch the downstream build info from jenkins
    requests.packages.urllib3.disable_warnings()
    req = Requester(None, None, baseurl=jenkins_url, ssl_verify=False)
    jenkins = api.Jenkins(jenkins_url, requester=req)
    assert jenkins.get_jobs_list()  # A test we are logged in
    job = jenkins.get_job(build_job_name)
    build = job.get_build(build_job_build_number)

    # Gather the fingerprints that link together the jobs
    downstream_jobs_names = build.job.get_downstream_job_names()
    fingerprint_data = build.get_data(
        "%s?depth=2&tree=fingerprint[fileName,usage[name,ranges[ranges[start,end]]]]"
        % build.python_api_url(build.baseurl)
    )
    usages = []  # Usages are a record of a fingerprint being used in specific test runs

    for fingerprint in fingerprint_data["fingerprint"]:
        if fingerprint["fileName"] == "build_info.txt":
            usages.append(fingerprint["usage"])

    # Use the fingerprint data to get a unique list of test runs for the build
    unique_runs = compile_unique_runs(usages)

    # Select the best run (most recent pass, or failure if no passes)
    test_runs = []
    for job_name, unique_build_nums in unique_runs.iteritems():
        if (job_name in downstream_jobs_names) and (job_name in valid_test_jobs):
            best_runs = get_best_runs(job_name, unique_build_nums)
            if best_runs:
                test_runs.extend(best_runs)

    logging.info("Final list of runs we will report on '%s'" % test_runs)

    # Gather test and coverage reports from test jobs
    mkdir_p("coverage_files")
    mkdir_p("test_reports")
    mkdir_p("linking_artifacts")

    for test_run in test_runs:
        artifacts = test_run.get_artifact_dict()

        if ".coverage" in artifacts:
            coverage_report = artifacts[".coverage"]
            coverage_report.save("coverage_files/.coverage.%s" % test_run.job.name)

        test_reports = [v for k, v in artifacts.iteritems() if re.match(".*test|TEST.*.xml", k)]
        logging.info("Found the following reports for %s: '%s'" % (test_run.name, [r.filename for r in test_reports]))
        mkdir_p("test_reports/%s" % os.path.normpath(test_run.name))

        for test_report in test_reports:
            test_report.save_to_dir("test_reports/%s/" % os.path.normpath(test_run.name))

        # Also download the test_info.txt for each so we still get a link even if no
        # report was generated in the run.
        if "test_info.txt" in artifacts:
            artifacts["test_info.txt"].save("linking_artifacts/%s_test_info.txt" % test_run.name)

    # Ensure all of the jobs required to be run to land are passing
    logging.info("Requiring these tests: '%s'" % required_tests)
    found_tests = set([t.job.name for t in test_runs if os.listdir("test_reports/%s" % t.name)])
    logging.info("Found these tests: '%s'" % found_tests)
    missing_tests = required_tests.difference(found_tests)

    if missing_tests:
        print(
            "MISSING TEST RESULTS! Did not find an expected test report for these tests: '%s'."
            % ", ".join(missing_tests)
        )
        exit(1)

    # Check if there were test failures
    failing_tests = [t for t in test_runs if not t.is_good()]
    if failing_tests:
        logging.info("Failing tests: '%s'" % failing_tests)
        print("FAILED")
        exit(1)
    else:
        print("SUCCESS")
