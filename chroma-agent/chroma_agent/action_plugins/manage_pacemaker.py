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


"""
Corosync verification
"""

import socket
import json
import time
import threading

from chroma_agent.lib.shell import AgentShell
from chroma_agent.lib.pacemaker import cibadmin, PacemakerConfig
from chroma_agent.log import daemon_log
from chroma_agent.chroma_common.lib.agent_rpc import agent_error, agent_result_ok, agent_ok_or_error
from manage_corosync import start_corosync, stop_corosync
from chroma_agent.lib.pacemaker import pacemaker_running
from chroma_agent.lib.corosync import corosync_running
from chroma_agent.lib.service_control import ServiceControl


# The window of time in which we count resource monitor failures
RSRC_FAIL_WINDOW = "20m"
# The number of times in the above window a resource monitor can fail
# before we migrate it
RSRC_FAIL_MIGRATION_COUNT = "3"


pacemaker_service = ServiceControl.create('pacemaker')
corosync_service = ServiceControl.create('corosync')


def _get_cluster_size():
    # you'd think there'd be a way to query the value of a property
    # such as "expected-quorum-votes" but there does not seem to be, so
    # just count nodes instead
    rc, stdout, stderr = AgentShell.run(["crm_node", "-l"])

    if not stdout:
        return 0

    n = 0
    for line in stdout.rstrip().split('\n'):
        node_id, name, status = line.split(" ")
        if status == "member" or status == "lost":
            n = n + 1

    return n


def _debug_corosync_pacemaker(value=None):
    # Just run some harmless pacemaker corosync commands to provide some output on stdout
    pacemaker_service.running
    corosync_service.running

    return value


def start_pacemaker():

    return agent_ok_or_error(pacemaker_service.start())


def stop_pacemaker():
    return agent_ok_or_error(pacemaker_service.stop())


def enable_pacemaker():
    return agent_ok_or_error(pacemaker_service.add() or
                             pacemaker_service.enable())


def configure_pacemaker():
    '''
    Configure pacemaker
    :return: Error string on failure, None on success
    '''
    # Corosync needs to be running for pacemaker -- if it's not, make
    # an attempt to get it going.
    if not corosync_service.running:
        error = corosync_service.restart()

        if error:
            return agent_error(error)

    # enable_pacemaker()
    # Agent.run_canned_error_message(['/sbin/service', 'pacemaker', 'restart'])

    for action in [enable_pacemaker, stop_pacemaker, start_pacemaker, _configure_pacemaker]:
        error = action()

        if error != agent_result_ok:
            return error

    # Now check that pacemaker is configured, by looking for our configuration flag.
    # Allow 1 minute - if nothing then return an error.
    # for timeout in range(0, 60):
    #     if PacemakerConfig().get_property_setvalue("intel_manager_for_lustre_configuration", "configured_by"):
    #         return agent_result_ok
    #     time.sleep(1)
    #
    # return agent_error("pacemaker_configuration_failed")
    time.sleep(1)
    return agent_result_ok


def _configure_pacemaker():
    '''
    Configure pacemaker if this node is the dc.

    :return: agent_ok if no error else returns an agent_error
    '''
    pc = PacemakerConfig()

    if not pc.is_dc:
        daemon_log.info("Skipping (global) pacemaker configuration because I am not the DC")
        return agent_result_ok

    daemon_log.info("Configuring (global) pacemaker configuration because I am the DC")

    # ignoring quorum should only be done on clusters of 2
    if len(pc.nodes) > 2:
        no_quorum_policy = "stop"
    else:
        no_quorum_policy = "ignore"

    error = _unconfigure_fencing()

    if error:
        return agent_error(error)

    # this could race with other cluster members to make sure
    # any errors are only due to it already existing
    try:
        cibadmin(["--create", "-o", "resources", "-X",
                  "<primitive class=\"stonith\" id=\"st-fencing\" type=\"fence_chroma\"/>"])
    except Exception as e:
        rc, stdout, stderr = AgentShell.run(['crm_resource', '--locate',
                                             '--resource', "st-fencing"])
        if rc == 0:                     # no need to do the rest if another member is already doing it
            return agent_result_ok
        else:
            return agent_error(e.message)

    pc.create_update_properyset("cib-bootstrap-options",
                                {"no-quorum-policy": no_quorum_policy,
                                 "symmetric-cluster": "true",
                                 "cluster-infrastructure": "openais",
                                 "stonith-enabled": "false"})

    def set_rsc_default(name, value):
        '''

        :param name: attribute to set
        :param value: value to set
        :return: None if an error else a canned error message
        '''
        return AgentShell.run_canned_error_message(["crm_attribute", "--type", "rsc_defaults",
                                                    "--attr-name", name, "--attr-value", value])

    error = set_rsc_default("resource-stickiness", "1000") or \
            set_rsc_default("failure-timeout", RSRC_FAIL_WINDOW) or \
            set_rsc_default("migration-threshold", RSRC_FAIL_MIGRATION_COUNT)

    if error:
        return agent_error(error)

    # Finally mark who configured it.
    pc.create_update_properyset("intel_manager_for_lustre_configuration",
                                {"configured_by": socket.gethostname()})

    return agent_result_ok


def configure_fencing(agents):
    pc = PacemakerConfig()
    node = pc.get_node(socket.gethostname())

    node.clear_fence_attributes()

    if isinstance(agents, basestring):
        # For CLI debugging
        agents = json.loads(agents)

    for idx, agent in enumerate(agents):
        node.set_fence_attributes(idx, agent)

    pc.create_update_properyset("cib-bootstrap-options",
                                {"stonith-enabled": "true" if (len(agents) > 0) else "false"})

    # Finally mark who configured it.
    pc.create_update_properyset("intel_manager_for_lustre_configuration",
                                {"stonith_enabled_disabled_by": socket.gethostname()})


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

    return agent_ok_or_error(pacemaker_service.stop() or
                             pacemaker_service.disable())


def _unconfigure_fencing():
    try:
        cibadmin(["--delete", "-o", "resources", "-X",
                  "<primitive class=\"stonith\" id=\"st-fencing\" type=\"fence_chroma\"/>"])

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
    rc, stdout, stderr = AgentShell.run(['crm_node', '-l'])
    node_id = None
    for line in stdout.split('\n'):
        node_id, name, status = line.split(" ")
        if name == nodename:
            break
    AgentShell.try_run(['crm_node', '--force', '-R', node_id])
    cibadmin(["--delete", "-o", "nodes", "-X",
              "<node uname=\"%s\"/>" % nodename])
    cibadmin(["--delete", "-o", "nodes", "--crm_xml",
              "<node_state uname=\"%s\"/>" % nodename])


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


ACTIONS = [start_pacemaker, stop_pacemaker,
           enable_pacemaker, configure_pacemaker, unconfigure_pacemaker,
           configure_fencing, unconfigure_fencing,
           set_node_standby, set_node_online,
           delete_node]
