#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import re
import os
from chroma_agent import shell
from chroma_agent.crypto import Crypto
from chroma_agent.store import AgentStore

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

REPO_PATH = "/etc/yum.repos.d/Intel-Lustre-Manager.repo"


def configure_repo(remote_url, repo_path=REPO_PATH):
    crypto = Crypto(AgentStore.libdir())
    open(repo_path, 'w').write(REPO_CONTENT.format(remote_url, crypto.AUTHORITY_FILE, crypto.PRIVATE_KEY_FILE, crypto.CERTIFICATE_FILE))


def unconfigure_repo(repo_path=REPO_PATH):
    if os.path.exists(repo_path):
        os.remove(repo_path)


def update_packages():
    shell.try_run(['yum', '-y', 'update'])


def install_packages(packages, force_dependencies = False):
    """
    force_dependencies causes explicit evaluation of dependencies, and installation
    of any specific-version dependencies are satisfied even if
    that involves installing an older package than is already installed.
    Primary use case is installing lustre-modules, which depends on a
    specific kernel package.

    :param packages: List of strings, yum package names
    :param force_dependencies: If True, ensure dependencies are installed even
                               if more recent versions are available.
    :return:
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


ACTIONS = [configure_repo, unconfigure_repo, update_packages, install_packages, kernel_status]
CAPABILITIES = ['manage_updates']
