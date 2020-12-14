# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import socket
import sys

from netaddr import IPNetwork, IPAddress


def find_subnet(network, prefixlen):
    """Given a network, find another as big in RFC-1918 space
    passes for these tests:
    192.168.1.0/24
    10.0.1.0/24
    10.128.0.0/9
    10.127.255.254/9
    10.255.255.255/32
    """
    _network = IPNetwork("%s/%s" % (network, prefixlen))
    if _network >= IPNetwork("10.0.0.0/8") and _network < IPAddress("10.255.255.255"):
        if _network >= IPNetwork("10.128.0.0/9"):
            shadow_network = IPNetwork("10.0.0.0/%s" % prefixlen)
        else:
            shadow_network = IPNetwork("10.128.0.0/%s" % prefixlen)
    else:
        shadow_network = IPNetwork("10.0.0.0/%s" % prefixlen)

    return shadow_network


def subscribe_multicast(interface):
    """subscribe to the mcast addr"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(
        socket.IPPROTO_IP,
        socket.IP_MULTICAST_IF,
        socket.inet_aton(interface.ipv4_address),
    )
    mreq = socket.inet_aton(interface.mcastaddr) + socket.inet_aton(interface.ipv4_address)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    sock.bind(("", 52122))

    return sock
