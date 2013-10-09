#
# INTEL CONFIDENTIAL
#
# Copyright 2013 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


import subprocess
from chroma_agent.device_plugins.action_runner import CallbackAfterResponse
from chroma_agent.device_plugins import lustre
from chroma_agent.log import daemon_log

import re
import os
from chroma_agent import shell, config
from chroma_agent.crypto import Crypto

REPO_CONTENT = """
[Intel Lustre Manager]
name=Intel Lustre Manager updates
baseurl={0}
enabled=1
gpgcheck=0
sslverify = 1
sslcacert = {1}
sslclientkey = {2}
sslclientcert = {3}
"""

REPO_PATH = "/etc/yum.repos.d/Intel-Lustre-Agent.repo"


def configure_repo(remote_url, repo_path=REPO_PATH):
    crypto = Crypto(config.path)
    open(repo_path, 'w').write(REPO_CONTENT.format(remote_url, crypto.AUTHORITY_FILE, crypto.PRIVATE_KEY_FILE, crypto.CERTIFICATE_FILE))


def unconfigure_repo(repo_path=REPO_PATH):
    if os.path.exists(repo_path):
        os.remove(repo_path)


def update_packages(repos, packages):
    """

    Updates all packages from the repos in 'repos'.

    :param repos: List of strings, each is a yum repos to include in the update
    :param packages: List of packages to force dependencies for, e.g. specify
                     lustre-modules here to insist that the dependencies of that
                     are installed even if they're older than an installed package.
    :return: None if no updates were installed, else a package report of the format
             given by the lustre device plugin
    """

    shell.try_run(['yum', 'clean', 'all'])

    updates_stdout = shell.try_run(['repoquery', '--disablerepo=*', "--enablerepo=%s" % ",".join(repos), "--pkgnarrow=updates", "-a"])
    update_packages = updates_stdout.strip().split("\n")

    if not update_packages:
        return None

    if packages:
        out = shell.try_run(['repoquery', '--requires'] + list(packages))
        force_installs = []
        for requirement in [l.strip() for l in out.strip().split("\n")]:
            match = re.match("([^\)/]*) = (.*)", requirement)
            if match:
                require_package, require_version = match.groups()
                force_installs.append("%s-%s" % (require_package, require_version))

        if force_installs:
            shell.try_run(['yum', 'install', '-y'] + force_installs)

    # We are only updating named packages from our repoquery of the specified repos, but
    # this invokation of yum does not disable any repos, so we may pull in dependencies
    # from other repos such as the main CentOS one.
    shell.try_run(["yum", "-y", "update"] + update_packages)

    return lustre.scan_packages()


def install_packages(packages, force_dependencies=False):
    """
    force_dependencies causes explicit evaluation of dependencies, and installation
    of any specific-version dependencies are satisfied even if
    that involves installing an older package than is already installed.
    Primary use case is installing lustre-modules, which depends on a
    specific kernel package.

    :param packages: List of strings, yum package names
    :param force_dependencies: If True, ensure dependencies are installed even
                               if more recent versions are available.
    :return: A package report of the format given by the lustre device plugin
    """
    if force_dependencies:
        out = shell.try_run(['repoquery', '--requires'] + list(packages))
        force_installs = []
        for requirement in [l.strip() for l in out.strip().split("\n")]:
            match = re.match("([^\)/]*) = (.*)", requirement)
            if match:
                require_package, require_version = match.groups()
                force_installs.append("%s-%s" % (require_package, require_version))

        shell.try_run(['yum', 'install', '-y'] + force_installs)

    shell.try_run(['yum', 'install', '-y'] + list(packages))

    return lustre.scan_packages()


def kernel_status(kernel_regex):
    """
    :param kernel_regex: Regex which kernels must match to be considered for 'latest'
    :return: {'running': {'kernel-X.Y.Z'}, 'latest': <'kernel-A.B.C' or None>}
    """
    running_kernel = "kernel-%s" % shell.try_run(["uname", "-r"]).strip()
    installed_kernel_stdout = shell.try_run(["rpm", "-q", "kernel", "--qf", "%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH} %{INSTALLTIME}\\n"])

    latest_matching_kernel = None
    for line in [l.strip() for l in installed_kernel_stdout.strip().split("\n")]:
        package, installtime = line.split()
        installtime = int(installtime)

        if re.match(kernel_regex, package):
            if not latest_matching_kernel or installtime > latest_matching_kernel[1]:
                latest_matching_kernel = (package, installtime)

    return {
        'running': running_kernel,
        'latest': latest_matching_kernel[0] if latest_matching_kernel else None
    }


def restart_agent():
    def _shutdown():
        daemon_log.info("Restarting agent")
        # Use subprocess.Popen instead of try_run because we don't want to
        # wait for completion.
        subprocess.Popen(['service', 'chroma-agent', 'restart'])

    raise CallbackAfterResponse(None, _shutdown)


ACTIONS = [configure_repo, unconfigure_repo, update_packages, install_packages, kernel_status, restart_agent]
CAPABILITIES = ['manage_updates']
