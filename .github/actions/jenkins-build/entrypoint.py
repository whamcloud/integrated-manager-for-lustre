#!/usr/bin/env python3

import jenkins
import sys
import time


def mandatory_arg(idx):
    try:
        x = sys.argv[idx].strip()
    except IndexError:
        x = ""

    if x == "":
        raise ValueError("Required field missing")

    return x


def get_build_info(job_name: str, build_num):
    try:
        return server.get_build_info(job_name, build_num)
    except jenkins.JenkinsException:
        return None


def get_build_result(job_name: str, build_num):
    info = get_build_info(job_name, build_num) or {}

    return info.get("result")


JENKINS_URL = mandatory_arg(1)
JENKINS_TOKEN = mandatory_arg(2)
JENKINS_USER = mandatory_arg(3)
JOB_NAME = mandatory_arg(4)
BRANCH = mandatory_arg(5)
SHA = mandatory_arg(6)

server = jenkins.Jenkins(JENKINS_URL, username=JENKINS_USER, password=JENKINS_TOKEN)

next_build_num = server.get_job_info(JOB_NAME)["nextBuildNumber"]

server.build_job(JOB_NAME, {"ghprbSourceBranch": BRANCH, "ghprbActualCommit": SHA})

print("Waiting for build completion...")

tick = 0

while not (result := get_build_result(JOB_NAME, next_build_num)) and tick < 10:
    time.sleep(30)

    tick += 1


info = get_build_info(JOB_NAME, next_build_num)

print(f"::set-output name=job_url::{info.get('url')}")

if result != "SUCCESS":
    exit(1)
