#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import avahi
import dbus

__all__ = ["ZeroconfService"]


class ZeroconfServiceException(Exception):
    pass


class ZeroconfService:
    """A simple class to publish a network service with zeroconf using
    avahi.

    """

    def __init__(self, name, port, stype="_chroma-agent._tcp",
                 domain="", host="", text=""):
        self.name = name
        self.stype = stype
        self.domain = domain
        self.host = host
        self.port = port
        self.text = text

    def publish(self):
        bus = dbus.SystemBus()
        try:
            server = dbus.Interface(
                             bus.get_object(
                                     avahi.DBUS_NAME,
                                     avahi.DBUS_PATH_SERVER),
                            avahi.DBUS_INTERFACE_SERVER)

            g = dbus.Interface(
                        bus.get_object(avahi.DBUS_NAME,
                                       server.EntryGroupNew()),
                        avahi.DBUS_INTERFACE_ENTRY_GROUP)

            g.AddService(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC, dbus.UInt32(0),
                         self.name, self.stype, self.domain, self.host,
                         dbus.UInt16(self.port), self.text)

            g.Commit()
            self.group = g
        except dbus.DBusException, e:
            if e.get_dbus_name() == \
                'org.freedesktop.DBus.Error.ServiceUnknown':
                raise ZeroconfServiceException("NotRunning")
            else:
                raise

    def unpublish(self):
        self.group.Reset()
