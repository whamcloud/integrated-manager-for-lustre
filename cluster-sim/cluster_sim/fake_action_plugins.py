#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import threading
import time
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

                # This is going to try to join() me, so call it from a different thread
                class KillLater(threading.Thread):
                    def run(self):
                        # FIXME race, hoping that this is long enough for the job response
                        # to make it home
                        time.sleep(10)
                        server.crypto.delete()
                        sim.stop_server(server.fqdn)
                KillLater().start()

                return
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
                log.debug(">>failback")
                rc = self._server._cluster.failback(kwargs['ha_label'])
                log.debug("<<failback %s" % rc)
                return rc
            elif cmd == 'writeconf_target':
                pass
            elif cmd == 'set_conf_param':
                self._server.set_conf_param(kwargs['key'], kwargs.get('value', None))
            else:
                try:
                    fn = getattr(self._server, cmd)
                except AttributeError:
                    raise RuntimeError("Unknown command %s" % cmd)
                else:
                    return fn(**kwargs)
