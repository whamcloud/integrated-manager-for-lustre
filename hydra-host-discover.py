#!/usr/bin/env python
#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

import dbus
import gobject
import avahi
from dbus.mainloop.glib import DBusGMainLoop
import daemon
import daemon.pidlockfile
import urllib
import json

TYPE = "_hydra-agent._tcp"


def service_resolved(interface, protocol, name, stype, domain, host,
                     aprotocol, address, port, txt, flags):

    hostname = host[0:host.rfind(".")]

    u = urllib.urlopen('http://localhost/api/add_host/',
                       data=urllib.urlencode({'hostname': hostname}))
    j = json.load(u)

    if not j['success']:
        # what, oh what to do, really?
        print "adding host %s failed %s" % (hostname, j['errors'])


def print_error(err):
    print err


def myhandler(interface, protocol, name, stype, domain, flags):
    if flags & avahi.LOOKUP_RESULT_LOCAL:
        # local service, skip
        pass

    server.ResolveService(interface, protocol, name, stype, domain,
                          avahi.PROTO_UNSPEC, dbus.UInt32(0),
                          reply_handler=service_resolved,
                          error_handler=print_error)

with daemon.DaemonContext(pidfile = \
           daemon.pidlockfile.PIDLockFile('/var/run/hydra-host-discover.pid')):

    loop = DBusGMainLoop()
    bus = dbus.SystemBus(mainloop=loop)
    server = dbus.Interface(bus.get_object(avahi.DBUS_NAME,
                                           avahi.DBUS_PATH_SERVER),
                            avahi.DBUS_INTERFACE_SERVER)
    b = dbus.Interface(bus.get_object(avahi.DBUS_NAME,
                                      server.ServiceBrowserNew(avahi.IF_UNSPEC,
                                                               avahi.PROTO_UNSPEC,
                                                               TYPE, 'local',
                                                               dbus.UInt32(0))),
                       avahi.DBUS_INTERFACE_SERVICE_BROWSER)
    b.connect_to_signal('ItemNew', myhandler)

    gobject.MainLoop().run()
