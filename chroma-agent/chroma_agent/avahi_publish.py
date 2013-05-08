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
