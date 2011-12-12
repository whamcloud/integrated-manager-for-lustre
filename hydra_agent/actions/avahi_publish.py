import avahi
import dbus
import time
import os
import daemon, daemon.pidlockfile
import lockfile

__all__ = ["ZeroconfService"]

class ZeroconfService:
    """A simple class to publish a network service with zeroconf using
    avahi.

    """

    def __init__(self, name, port, stype="_hydra-agent._tcp",
                 domain="", host="", text=""):
        self.name = name
        self.stype = stype
        self.domain = domain
        self.host = host
        self.port = port
        self.text = text

    def publish(self):
        bus = dbus.SystemBus()
        server = dbus.Interface(
                         bus.get_object(
                                 avahi.DBUS_NAME,
                                 avahi.DBUS_PATH_SERVER),
                        avahi.DBUS_INTERFACE_SERVER)

        g = dbus.Interface(
                    bus.get_object(avahi.DBUS_NAME,
                                   server.EntryGroupNew()),
                    avahi.DBUS_INTERFACE_ENTRY_GROUP)

        g.AddService(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC,dbus.UInt32(0),
                     self.name, self.stype, self.domain, self.host,
                     dbus.UInt16(self.port), self.text)

        g.Commit()
        self.group = g

    def unpublish(self):
        self.group.Reset()


def publish_daemon(args):
    context = daemon.DaemonContext(pidfile = daemon.pidlockfile.PIDLockFile('/var/run/hydra-agent.pid'))
    context.open()
    try:
        service = ZeroconfService(name="%s" % os.uname()[1], port=22)
        service.publish()
        while True:
            time.sleep(86400)
        # don't need to call service.unpublish() since the service
        # will be unpublished when this daemon exits
    finally:
        context.close()
