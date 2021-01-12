# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

from chroma_agent.lib.shell import AgentShell
from chroma_agent.log import daemon_log


def yum_util(action, packages=[], fromrepo=None, enablerepo=None, narrow_updates=False):
    """
    A wrapper to perform yum actions in encapsulated way.
    :param action:  clean, install, remove, update, requires etc
    :param packages: Packages to install or remove
    :param fromrepo: The repo the action should be carried out from, others are disabled.
    :param enablerepo: The repo to enable for the action, others are not disabled or enabled
    :param narrow_updates: ?
    :return: No return but throws CommandExecutionError on error.
    """

    if fromrepo and enablerepo:
        raise ValueError("Cannot provide fromrepo and enablerepo simultaneously")

    repo_arg = []
    valid_rc_values = [0]  # Some errors values other than 0 are valid.
    tries = 2
    if fromrepo:
        repo_arg = ["--disablerepo=*"] + ["--enablerepo=%s" % r for r in fromrepo]
    elif enablerepo:
        repo_arg = ["--enablerepo=%s" % r for r in enablerepo]
    if narrow_updates and action == "query":
        repo_arg.extend(["--upgrades"])

    if action == "clean":
        cmd = ["yum", "clean", "all"] + (repo_arg if repo_arg else ["--enablerepo=*"])
    elif action == "install":
        cmd = ["yum", "install", "-y", "--exclude", "kernel-debug"] + repo_arg + list(packages)
    elif action == "remove":
        cmd = ["yum", "remove", "-y"] + repo_arg + list(packages)
    elif action == "update":
        cmd = ["yum", "update", "-y", "--exclude", "kernel-debug"] + repo_arg + list(packages)
    elif action == "requires":
        cmd = ["repoquery", "--requires"] + repo_arg + list(packages)
    elif action == "query":
        cmd = ["repoquery"] + repo_arg + list(packages)
    elif action == "repoquery":
        cmd = (
            ["repoquery", "--show-duplicates"]
            + repo_arg
            + ["--queryformat=%{EPOCH} %{NAME} " "%{VERSION} %{RELEASE} %{ARCH}"]
        )
    else:
        raise RuntimeError("Unknown yum util action %s" % action)

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
            if action == "install":
                AgentShell.run(["yum", "clean", "metadata"])
            daemon_log.info("HYD-3885 Retrying yum command '%s'" % " ".join(cmd))
            if hyd_3885 == 0:
                daemon_log.info("HYD-3885 Retry yum command failed '%s'" % " ".join(cmd))
                raise AgentShell.CommandExecutionError(result, cmd)  # Out of retries so raise for the caller..
