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


import threading
from chroma_agent import shell

from chroma_agent.device_plugins.action_runner import CallbackAfterResponse
from cluster_sim.log import log
from cluster_sim.fake_device_plugins import FakeDevicePlugins


class FakeActionPlugins():
    """
    Provides action plugin execution by passing through to the other
    fake classes.  Where the real ActionPluginManager delegates running
    actions to the plugins, this class has all the actions built-in.
    """
    def __init__(self, server, simulator):
        self._label_counter = 0
        self._server = server
        self._lock = threading.Lock()
        self._simulator = simulator

    @property
    def capabilities(self):
        return ['manage_targets']

    def run(self, cmd, kwargs):

        # This is a little hackish: we don't actually separate the thread_state for
        # each simulated agent (they mostly don't even shell out when simulated) but
        # do this to avoid the subprocess log building up indefinitely.
        shell.thread_state = shell.ThreadState()

        log.debug("FakeActionPlugins: %s %s" % (cmd, kwargs))
        with self._lock:
            if cmd == 'device_plugin':
                device_plugins = FakeDevicePlugins(self._server)
                if kwargs['plugin']:
                    return {kwargs['plugin']: device_plugins.get(kwargs['plugin'])(None).start_session()}
                else:
                    data = {}
                    for plugin, klass in device_plugins.get_plugins().items():
                        data[plugin] = klass(None).start_session()
                    return data

            elif cmd == 'configure_rsyslog':
                return
            elif cmd == 'configure_ntp':
                return
            elif cmd == 'deregister_server':
                sim = self._simulator
                server = self._server

                class StopServer(threading.Thread):
                    def run(self):
                        sim.stop_server(server.fqdn)

                def kill():
                    server.crypto.delete()
                    # Got to go and run stop_server in another thread, because it will try
                    # to join all the agent threads (including the one that is running this
                    # callback)
                    StopServer().start()

                raise CallbackAfterResponse(None, kill)
            elif cmd == 'shutdown_server':
                server = self._server

                def _shutdown():
                    server.shutdown(simulate_shutdown = True)

                raise CallbackAfterResponse(None, _shutdown)
            elif cmd == 'reboot_server':
                server = self._server

                def _reboot():
                    server.shutdown(simulate_shutdown = True, reboot = True)

                raise CallbackAfterResponse(None, _reboot)
            elif cmd == 'unconfigure_ntp':
                return
            elif cmd == 'unconfigure_rsyslog':
                return
            elif cmd == 'lnet_scan':
                if self._server.state['lnet_up']:
                    return self._server.nids
                else:
                    raise RuntimeError('LNet is not up')
            elif cmd == 'failover_target':
                return self._server._cluster.failover(kwargs['ha_label'])
            elif cmd == 'failback_target':
                rc = self._server._cluster.failback(kwargs['ha_label'])
                return rc
            elif cmd == 'set_conf_param':
                self._server.set_conf_param(kwargs['key'], kwargs.get('value', None))
            elif cmd in ['configure_corosync', 'unconfigure_corosync']:
                return
            elif cmd in ['configure_pacemaker', 'unconfigure_pacemaker']:
                return
            elif cmd == 'configure_repo':
                return
            elif cmd in ['update_packages', 'install_packages']:
                return
            elif cmd == 'kernel_status':
                return {
                    'running': 'fake_kernel-0.1',
                    'latest': 'fake_kernel-0.1'
                }
            elif cmd in ['configure_fencing', 'unconfigure_fencing']:
                return
            elif cmd == "host_corosync_config":
                return {}
            else:
                try:
                    fn = getattr(self._server, cmd)
                except AttributeError:
                    raise RuntimeError("Unknown command %s" % cmd)
                else:
                    return fn(**kwargs)
