#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2015 Intel Corporation All Rights Reserved.
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
import re
import os
import platform

from chroma_agent.chroma_common.lib import shell
from chroma_agent.device_plugins.action_runner import CallbackAfterResponse
from chroma_agent.device_plugins import lustre
from chroma_agent.log import daemon_log
from chroma_agent import config
from chroma_agent.crypto import Crypto
from chroma_agent.lib.yum_utils import yum_util, yum_check_update

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

from chroma_agent.device_plugins.lustre import REPO_PATH


def configure_repo(remote_url, repo_path=REPO_PATH):
    crypto = Crypto(config.path)
    open(repo_path, 'w').write(REPO_CONTENT.format(remote_url, crypto.AUTHORITY_FILE, crypto.PRIVATE_KEY_FILE, crypto.CERTIFICATE_FILE))


def unconfigure_repo(repo_path=REPO_PATH):
    if os.path.exists(repo_path):
        os.remove(repo_path)


def update_profile(profile):
    '''
    Sets the profile to the profile_name by fetching the profile from the manager
    :param profile_name:
    :return: None is OK else an error String
    '''
    old_profile = config.get('settings', 'profile')

    '''
    This is an incomplete solution but the incompleteness is at the bottom of the stack and we need this as a fix up
    for 2.2 release.

    What really needs to happen here is that the profile contains the name of the packages to install and then this
    code would diff the old list and the new list and remove and add appropriately. For now we are just going to do that
    in a hard coded way using the managed property.

    To do this properly the profile needs to contain the packages and the endpoint needs to return them. We are going to
    need it and when we do this function and profiles will need to be extended.

    This code might want to use the update_pacakges as well but it's not clear and we are in a pickle here. This code is
    not bad and doesn't have bad knock on effects.
    '''

    if old_profile['managed'] != profile['managed']:
        if profile['managed']:
            action = 'install'
        else:
            action = 'remove'

        try:
            yum_util(action, enablerepo=["iml-agent"], packages=['chroma-agent-management'])
        except shell.CommandExecutionError as cee:
            return "Unable to set profile because yum returned %s" % cee.stdout

    config.update('settings', 'profile', profile)

    return None


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

    yum_util('clean')

    updates_stdout = yum_util('query', fromrepo=repos, narrow_updates=True)
    update_packages = updates_stdout.strip().split("\n")

    if not update_packages:
        return None

    if packages:
        out = yum_util('requires', packages=packages)
        force_installs = []
        for requirement in [l.strip() for l in out.strip().split("\n")]:
            match = re.match("([^\)/]*) = (.*)", requirement)
            if match:
                require_package, require_version = match.groups()
                force_installs.append("%s-%s" % (require_package, require_version))

        if force_installs:
            yum_util('install', enablerepo=repos, packages=force_installs)

    # We are only updating named packages from our repoquery of the specified repos, but
    # this invokation of yum does not disable any repos, so we may pull in dependencies
    # from other repos such as the main CentOS one.

    yum_util('update', packages=update_packages, enablerepo=repos)

    error = _check_HYD4050()

    if error:
        return {"error": error}

    return {'scan_packages': lustre.scan_packages()}


def install_packages(repos, packages, force_dependencies=False):
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

    yum_util('clean')

    if force_dependencies:
        out = yum_util('requires', enablerepo=repos, packages=packages)
        force_installs = []
        for requirement in [l.strip() for l in out.strip().split("\n")]:
            match = re.match("([^\)/]*) = (.*)", requirement)
            if match:
                require_package, require_version = match.groups()
                force_installs.append("%s-%s" % (require_package, require_version))

        yum_util('install', packages=force_installs, enablerepo=repos)

    yum_util('install', enablerepo=repos, packages=packages)

    # So now we have installed the packages requested, we will also make sure that any installed packages we
    # have that are already installed are updated to our presumably better versions.
    update_packages = yum_check_update(repos)

    if update_packages:
        daemon_log.debug("The following packages need update after we installed IML packages %s" % update_packages)
        yum_util('update', packages=update_packages, enablerepo=repos)

    error = _check_HYD4050()

    if error:
        return {"error": error}

    return {"scan_packages": lustre.scan_packages()}


def _check_HYD4050():
    '''
    HYD-4050 means that kernels are not installed with a default kernel or the initramfs isn't present.

    This function checks for these cases and returns an error message if a problem exists.

    return: None if everything is OK, error message if not.
    '''

    #  Make sure that there is an initramfs for the booting kernel
    try:
        default_kernel = shell.try_run(["grubby", "--default-kernel"]).strip()
    except shell.CommandExecutionError:
        return ("Unable to determine your default kernel.  "
                "This node may not boot successfully until grub "
                "is fixed to have a default kernel to boot.")

    default_kernel_version = default_kernel[default_kernel.find("-") + 1:]
    initramfs = "/boot/initramfs-%s.img" % default_kernel_version

    if not os.path.isfile(initramfs):
        return ("There is no initramfs (%s) for the default kernel (%s).  "
                "This node may not boot successfully until an initramfs "
                "is created." % (initramfs, default_kernel_version))

    return None


def kernel_status():
    """
    :return: {'running': {'kernel-X.Y.Z'}, 'required': <'kernel-A.B.C' or None>}
    """
    running_kernel = "kernel-%s" % shell.try_run(["uname", "-r"]).strip()
    try:
        required_kernel_stdout = shell.try_run(["rpm", "-qR", "lustre-modules"])
    except shell.CommandExecutionError:
        try:
            required_kernel_stdout = shell.try_run(["rpm", "-qR", "lustre-client-modules"])
        except shell.CommandExecutionError:
            required_kernel_stdout = None

    required_kernel = None
    if required_kernel_stdout:
        for line in required_kernel_stdout.split("\n"):
            if line.startswith('kernel'):
                required_kernel = "kernel-%s.%s" % (line.split(" = ")[1],
                                                    platform.machine())

    available_kernels = []
    for installed_kernel in shell.try_run(["rpm", "-q", "kernel"]).split("\n"):
        if installed_kernel:
            available_kernels.append(installed_kernel)

    return {
        'running': running_kernel,
        'required': required_kernel,
        'available': available_kernels
    }


def restart_agent():
    def _shutdown():
        daemon_log.info("Restarting agent")
        # Use subprocess.Popen instead of try_run because we don't want to
        # wait for completion.
        subprocess.Popen(['service', 'chroma-agent', 'restart'])

    raise CallbackAfterResponse(None, _shutdown)


ACTIONS = [configure_repo, unconfigure_repo, update_packages, install_packages, kernel_status, restart_agent, update_profile]
CAPABILITIES = ['manage_updates']
