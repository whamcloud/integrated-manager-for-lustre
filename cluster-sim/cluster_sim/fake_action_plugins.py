# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import threading

from chroma_agent.lib.shell import AgentShell, ResultStore
from chroma_agent.lib.pacemaker import PacemakerConfigurationError
from chroma_agent.device_plugins.action_runner import CallbackAfterResponse
from cluster_sim.log import log
from cluster_sim.fake_device_plugins import FakeDevicePlugins
from iml_common.lib.agent_rpc import agent_result_ok


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

    def run(self, cmd, agent_daemon_context, kwargs):

        # This is a little hackish: we don't actually separate the thread_state for
        # each simulated agent (they mostly don't even shell out when simulated) but
        # do this to avoid the subprocess log building up indefinitely.
        AgentShell.thread_state = ResultStore()

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

            elif cmd in ['configure_ntp',
                         'unconfigure_ntp',
                         'unconfigure_corosync',
                         'unconfigure_corosync2']:
                return agent_result_ok
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
            elif cmd == 'failover_target':
                self._server._cluster.failover(kwargs['ha_label'])
                return agent_result_ok
            elif cmd == 'failback_target':
                self._server._cluster.failback(kwargs['ha_label'])
                return agent_result_ok
            elif cmd == 'set_conf_param':
                self._server.set_conf_param(kwargs['key'], kwargs.get('value', None))
            elif cmd in ['configure_pacemaker',
                         'unconfigure_pacemaker',
                         'enable_pacemaker',
                         'configure_target_store',
                         'unconfigure_target_store',
                         'configure_repo']:
                return
            elif cmd == 'kernel_status':
                return {
                    'running': 'fake_kernel-0.1',
                    'required': 'fake_kernel-0.1',
                    'available': ['fake_kernel-0.1']
                }
            elif cmd in ['configure_fencing', 'unconfigure_fencing']:
                # This shouldn't happen if the fence reconfiguration logic
                # is working. Good to simulate a failure here in case of
                # regressions, though.
                if self._server.is_worker:
                    raise PacemakerConfigurationError()
                return
            elif cmd == "host_corosync_config":
                return {}
            elif cmd == 'mount_lustre_filesystems':
                for mountspec, mountpoint in kwargs['filesystems']:
                    self._server.add_client_mount(mountspec, mountpoint)
            elif cmd == 'unmount_lustre_filesystems':
                for mountspec, _ in kwargs['filesystems']:
                    self._server.del_client_mount(mountspec)
            elif cmd == 'configure_copytool':
                self._simulator.configure_hsm_copytool(self._server, **kwargs)
            elif cmd == 'unconfigure_copytool':
                self._simulator.unconfigure_hsm_copytool(kwargs['id'])
            elif cmd == 'start_monitored_copytool':
                self._simulator.start_monitored_copytool(self._server,
                                                         kwargs['id'])
            elif cmd == 'stop_monitored_copytool':
                self._simulator.stop_monitored_copytool(kwargs['id'])
            else:
                try:
                    fn = getattr(self._server, cmd)
                except AttributeError:
                    raise RuntimeError("Unknown command %s" % cmd)
                else:
                    return fn(**kwargs)
