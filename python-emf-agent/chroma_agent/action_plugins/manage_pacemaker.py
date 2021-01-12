# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


"""
Corosync verification
"""

import socket
import json
import time
import threading

from chroma_agent.lib.shell import AgentShell
from chroma_agent.lib.pacemaker import cibadmin, cibxpath, PacemakerConfig
from chroma_agent.log import daemon_log
from manage_corosync import start_corosync, stop_corosync
from chroma_agent.lib.pacemaker import pacemaker_running
from chroma_agent.lib.corosync import corosync_running
from emf_common.lib.service_control import ServiceControl
from emf_common.lib.agent_rpc import agent_error, agent_result_ok, agent_ok_or_error


# The window of time in which we count resource monitor failures
RSRC_FAIL_WINDOW = "20m"
# The number of times in the above window a resource monitor can fail
# before we migrate it
RSRC_FAIL_MIGRATION_COUNT = "3"

PACEMAKER_CONFIGURE_TIMEOUT = 120

pacemaker_service = ServiceControl.create("pacemaker")
corosync_service = ServiceControl.create("corosync")


def _get_cluster_size():
    # you'd think there'd be a way to query the value of a property
    # such as "expected-quorum-votes" but there does not seem to be, so
    # just count nodes instead
    rc, stdout, stderr = AgentShell.run_old(["crm_node", "-l"])

    if not stdout:
        return 0

    n = 0
    for line in stdout.rstrip().split("\n"):
        node_id, name, status = line.split(" ")
        if status == "member" or status == "lost":
            n = n + 1

    return n


def start_pacemaker():
    return agent_ok_or_error(pacemaker_service.start())


def stop_pacemaker():
    return agent_ok_or_error(pacemaker_service.stop())


def enable_pacemaker():
    return agent_ok_or_error(pacemaker_service.enable())


def configure_pacemaker():
    """
    Configure pacemaker
    :return: Error string on failure, None on success
    """
    # Corosync needs to be running for pacemaker -- if it's not, make
    # an attempt to get it going.
    if not corosync_service.running:
        error = corosync_service.restart()

        if error:
            return agent_error(error)

    for action in [
        enable_pacemaker,
        stop_pacemaker,
        start_pacemaker,
        _configure_pacemaker,
    ]:
        error = action()

        if error != agent_result_ok:
            return error

    time.sleep(1)
    return agent_result_ok


def _configure_pacemaker():
    """
    Configure pacemaker if this node is the dc.

    :return: agent_ok if no error else returns an agent_error
    """
    pc = PacemakerConfig()

    timeout_time = time.time() + PACEMAKER_CONFIGURE_TIMEOUT
    error = None

    while (pc.configured is False) and (time.time() < timeout_time):
        if pc.is_dc:
            daemon_log.info("Configuring (global) pacemaker configuration because I am the DC")

            error = _do_configure_pacemaker(pc)

            if error:
                return agent_error(error)
        else:
            daemon_log.info("Not configuring (global) pacemaker configuration because I am not the DC")

        time.sleep(10)

    if pc.configured is False:
        error = "Failed to configure (global) pacemaker configuration dc=%s" % pc.dc

    return agent_ok_or_error(error)


def _do_configure_pacemaker(pc):
    # ignoring quorum should only be done on clusters of 2
    if len(pc.nodes) > 2:
        no_quorum_policy = "stop"
    else:
        no_quorum_policy = "ignore"

    error = _unconfigure_fencing()

    if error:
        return error

    # this could race with other cluster members to make sure
    # any errors are only due to it already existing
    try:
        cibadmin(
            [
                "--create",
                "-o",
                "resources",
                "-X",
                '<primitive class="stonith" id="st-fencing" type="fence_chroma"/>',
            ]
        )
    except Exception as e:
        rc, stdout, stderr = AgentShell.run_old(["crm_resource", "--locate", "--resource", "st-fencing"])
        if rc == 0:  # no need to do the rest if another member is already doing it
            return None
        else:
            return e.message

    pc.create_update_properyset(
        "cib-bootstrap-options",
        {
            "no-quorum-policy": no_quorum_policy,
            "symmetric-cluster": "true",
            "cluster-infrastructure": "openais",
            "stonith-enabled": "true",
        },
    )

    def set_rsc_default(name, value):
        """

        :param name: attribute to set
        :param value: value to set
        :return: None if an error else a canned error message
        """
        return AgentShell.run_canned_error_message(
            [
                "crm_attribute",
                "--type",
                "rsc_defaults",
                "--attr-name",
                name,
                "--attr-value",
                value,
            ]
        )

    return (
        set_rsc_default("resource-stickiness", "1000")
        or set_rsc_default("failure-timeout", RSRC_FAIL_WINDOW)
        or set_rsc_default("migration-threshold", RSRC_FAIL_MIGRATION_COUNT)
    )


def configure_fencing(agents):
    pc = PacemakerConfig()
    node = pc.get_node(socket.gethostname())

    node.clear_fence_attributes()

    if isinstance(agents, basestring):
        # For CLI debugging
        agents = json.loads(agents)

    for idx, agent in enumerate(agents):
        node.set_fence_attributes(idx, agent)

    pc.create_update_properyset("cib-bootstrap-options", {"stonith-enabled": "true"})


def set_node_standby(node):
    pc = PacemakerConfig()
    node = pc.get_node(node)
    node.enable_standby()


def set_node_online(node):
    pc = PacemakerConfig()
    node = pc.get_node(node)
    node.disable_standby()


def _pacemaker_running():
    return pacemaker_service.running


def unconfigure_pacemaker():
    # only unconfigure if we are the only node in the cluster
    # but first, see if pacemaker is up to answer this
    if not _pacemaker_running():
        # and just skip doing this if it's not
        return agent_result_ok

    if _get_cluster_size() < 2:
        # last node, nuke the CIB
        cibadmin(["-f", "-E"])

    return agent_ok_or_error(pacemaker_service.stop() or pacemaker_service.disable())


def _unconfigure_fencing():
    try:
        cibadmin(
            [
                "--delete",
                "-o",
                "resources",
                "-X",
                '<primitive class="stonith" id="st-fencing" type="fence_chroma"/>',
            ]
        )

        return None
    except Exception as e:
        return e.message


def unconfigure_fencing():
    # only unconfigure if we are the only node in the cluster
    # but first, see if pacemaker is up to answer this
    if not _pacemaker_running():
        # and just skip doing this if it's not
        return 0

    if _get_cluster_size() > 1:
        return 0

    return agent_ok_or_error(_unconfigure_fencing())


def delete_node(nodename):
    rc, stdout, stderr = AgentShell.run_old(["crm_node", "-l"])
    node_id = None
    for line in stdout.split("\n"):
        node_id, name, status = line.split(" ")
        if name == nodename:
            break
    AgentShell.try_run(["crm_node", "--force", "-R", node_id])
    cibxpath("delete", '//nodes/node[@uname="{}"]'.format(nodename))
    cibxpath("delete", '//status/node_state[@uname="{}"]'.format(nodename))


# This is a required due to a short coming in the state-machine which is that transient states are not supported.
# For example: O1:Sa->Sb, requires O2:Sx and O3:Sf, But O3 requires O2 to go to Sy for the transition to Sf.
# If O2 is in Sy then when O2 transition to Sf to satisfy O3 it will hence fail the dependency test for O1.
# So work around known cases by hand, like this.

# Sadly we have to sequentialize these actions to ensure the correct outcome, which is not the best outcome. But
# a requirement at the moment.
class PreservePacemakerCorosyncState(object):
    lock = threading.Lock()

    def __enter__(self):
        PreservePacemakerCorosyncState.lock.acquire()

        try:
            self.pacemaker_is_running = pacemaker_running()
            self.corosync_is_running = corosync_running()

            start_corosync()
            start_pacemaker()
        except:
            PreservePacemakerCorosyncState.lock.release()
            raise

    def __exit__(self, exception_type, value, _traceback):
        try:
            if not self.pacemaker_is_running:
                stop_pacemaker()
            if not self.corosync_is_running:
                stop_corosync()
        finally:
            PreservePacemakerCorosyncState.lock.release()


ACTIONS = [
    start_pacemaker,
    stop_pacemaker,
    enable_pacemaker,
    configure_pacemaker,
    unconfigure_pacemaker,
    configure_fencing,
    unconfigure_fencing,
    set_node_standby,
    set_node_online,
    delete_node,
]
