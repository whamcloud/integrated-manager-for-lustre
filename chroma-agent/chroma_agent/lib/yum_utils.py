# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


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
    tries = 2
    if fromrepo:
        repo_arg = ['--disablerepo=*'] + ['--enablerepo=%s' % r for r in fromrepo]
    elif enablerepo:
        repo_arg = ['--enablerepo=%s' % r for r in enablerepo]
    if narrow_updates and action == 'query':
        repo_arg.extend(['--upgrades'])

    if action == 'clean':
        cmd = ['dnf', 'clean', 'all'] + (repo_arg if repo_arg else ["--enablerepo=*"])
    elif action == 'install':
        cmd = ['dnf', 'install', '--allowerasing', '-y', '--exclude', 'kernel-debug'] + \
               repo_arg + list(packages)
    elif action == 'remove':
        cmd = ['dnf', 'remove', '-y'] + repo_arg + list(packages)
    elif action == 'update':
        cmd = ['dnf', 'update', '--allowerasing', '-y', '--exclude', 'kernel-debug'] + \
               repo_arg + list(packages)
    elif action == 'requires':
        cmd = ['dnf', 'repoquery', '--requires'] + repo_arg + list(packages)
    elif action == 'query':
        cmd = ['dnf', 'repoquery', '--available'] + repo_arg + list(packages)
    elif action == 'repoquery':
        cmd = ['dnf', 'repoquery', '--available'] + repo_arg + ['--queryformat=%{EPOCH} %{NAME} %{VERSION} %{RELEASE} %{ARCH}']
    elif action == 'check-update':
        cmd = ['dnf', 'repoquery', '--queryformat=%{name} %{version}-%{release}.'
               '%{arch} %{repoid}', '--upgrades'] + repo_arg + \
            list(packages)
    else:
        raise RuntimeError('Unknown yum util action %s' % action)

    # This is a poor solution for HYD-3855 but not one that carries any known cost.
    # We sometimes see intermittent failures in test, and possibly out of test, that occur
    # 1 in 50 (estimate) times. yum commands are idempotent and so trying the command three
    # times has no downside and changes the estimated chance of fail to 1 in 12500.
    for hyd_3885 in range(tries, -1, -1):
        result = AgentShell.run(cmd)

        if result.rc in valid_rc_values:
            return result.stdout
        else:
            # if we were trying to install, clean the metadata before
            # trying again
            if action == 'install':
                AgentShell.run(['dnf', 'clean', 'metadata'])
            daemon_log.info("HYD-3885 Retrying yum command '%s'" % " ".join(cmd))
            if hyd_3885 == 0:
                daemon_log.info("HYD-3885 Retry yum command failed '%s'" % " ".join(cmd))
                raise AgentShell.CommandExecutionError(result, cmd)   # Out of retries so raise for the caller..


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
