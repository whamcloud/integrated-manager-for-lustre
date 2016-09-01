#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2016 Intel Corporation All Rights Reserved.
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


from chroma_agent.lib.shell import AgentShell
from chroma_agent.log import daemon_log


def yum_util(action, packages=[], fromrepo=None, enablerepo=None, narrow_updates=False):
    '''
    A wrapper to perform yum actions in encapsulated way.
    :param action:  clean, install, remove, update, requires etc
    :param packages: Packages to install or remove
    :param fromrepo: The repo the action should be carried out from, others are disabled.
    :param enablerepo: The repo to enable for the action, others are not disabled or enabled
    :param narrow_updates: ?
    :return: No return but throws CommandExecutionError on error.
    '''

    if fromrepo and enablerepo:
        raise ValueError("Cannot provide fromrepo and enablerepo simultaneously")

    repo_arg = []
    valid_rc_values = [0]                               # Some errors values other than 0 are valid.
    if fromrepo:
        repo_arg = ['--disablerepo=*', '--enablerepo=%s' % ','.join(fromrepo)]
    elif enablerepo:
        repo_arg = ['--enablerepo=%s' % ','.join(enablerepo)]
    if narrow_updates and action == 'query':
        repo_arg.extend(['--pkgnarrow=updates', '-a'])

    if action == 'clean':
        cmd = ['yum', 'clean', 'all'] + (repo_arg if repo_arg else ["--enablerepo=*"])
    elif action == 'install':
        cmd = ['yum', 'install', '-y'] + repo_arg + list(packages)
    elif action == 'remove':
        cmd = ['yum', 'remove', '-y'] + repo_arg + list(packages)
    elif action == 'update':
        cmd = ['yum', 'update', '-y'] + repo_arg + list(packages)
    elif action == 'requires':
        cmd = ['repoquery', '--requires'] + repo_arg + list(packages)
    elif action == 'query':
        cmd = ['repoquery'] + repo_arg + list(packages)
    elif action == 'repoquery':
        cmd = ['repoquery'] + repo_arg + ['-a', '--qf=%{EPOCH} %{NAME} %{VERSION} %{RELEASE} %{ARCH}']
    elif action == 'check-update':
        cmd = ['yum', 'check-update', '-q'] + repo_arg + list(packages)
        valid_rc_values = [0, 100]                      # check-update returns 100 if updates are available.
    else:
        raise RuntimeError('Unknown yum util action %s' % action)

    # This is a poor solution for HYD-3855 but not one that carries any known cost.
    # We sometimes see intermittent failures in test, and possibly out of test, that occur
    # 1 in 50 (estimate) times. yum commands are idempotent and so trying the command three
    # times has no downside and changes the estimated chance of fail to 1 in 12500.
    for hyd_3885 in range(2, -1, -1):
        rc, stdout, stderr = AgentShell.run_old(cmd)

        if rc in valid_rc_values:
            return stdout
        else:
            daemon_log.info("HYD-3885 Retrying yum command '%s'" % " ".join(cmd))
            if hyd_3885 == 0:
                daemon_log.info("HYD-3885 Retry yum command failed '%s'" % " ".join(cmd))
                raise AgentShell.CommandExecutionError(AgentShell.RunResult(rc, stdout, stderr, False), cmd)   # Out of retries so raise for the caller..


def yum_check_update(repos):
    '''
    Uses yum check_update -q to return a list of packages from the repos passed in that require an update

    Will raise a CommandExecutionError if yum throws unexpected errors.

    :param repos: The repos to check for update
    :return: List of packages that require an update.
    '''
    packages = []

    yum_response = yum_util('check-update', fromrepo=repos)

    for line in filter(None, yum_response.split('\n')):
        elements = line.split()

        # Valid lines have 3 elements with the third entry being one of the repos anything else should be ignored but logged
        if len(elements) == 3 and (elements[2] in repos):
            packages.append(elements[0])
        else:
            daemon_log.warning("yum check_update found unknown response of: %s\nIn: %s\nLooking at: repos %s" % (line, yum_response, repos))

    return packages
