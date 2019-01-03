# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from chroma_core.services import log_register
from chroma_core.models import SyslogEvent, ClientConnectEvent, ManagedHost
from django.db import transaction
import logging
import re

syslog_events_log = log_register("syslog_events")

_re_cache = {}


def _re_find_one_in_many(haystack, needles):
    """Find the first instance of any of 'needles' in haystack"""
    if not isinstance(needles, tuple):
        needles = tuple(needles)

    try:
        expr = _re_cache[needles]
    except:
        expr = re.compile("|".join([re.escape(n) for n in needles]))
        _re_cache[needles] = expr

    result = expr.search(haystack)
    if result:
        return result.group(0)
    else:
        return None


def _plain_find_one_in_many(haystack, needles):
    for n in needles:
        if haystack.find(n) != -1:
            return n


# use the plain version for now
# in the future, we can switch to REs or a combination
find_one_in_many = _plain_find_one_in_many


def _get_word_after(string, after):
    s = string.find(after) + len(after)
    l = string[s:].find(" ")
    return string[s : s + l]


#
# acceptor port is already being used
#
# LustreError: 122-1: Can't start acceptor on port 988: port already in use
def port_used_handler(message, host):
    SyslogEvent.register_event(severity=logging.ERROR, alert_item=host, message_str="Lustre port already being used")


#
# client connected to services:
#
# Lustre: 5629:0:(ldlm_lib.c:877:target_handle_connect()) lustre-MDT0000: connection from 26959b68-1208-1fca-1f07-da2dc872c55f@192.168.122.218@tcp t0 exp 0000000000000000 cur 1317994929 last 0
# Lustre: 27559:0:(ldlm_lib.c:871:target_handle_connect()) lustre-OST0001: connection from 26959b68-1208-1fca-1f07-da2dc872c55f@192.168.122.218@tcp t0 exp 0000000000000000 cur 1317994930 last 0
# Lustre: 9150:0:(ldlm_lib.c:871:target_handle_connect()) lustre-OST0000: connection from 26959b68-1208-1fca-1f07-da2dc872c55f@192.168.122.218@tcp t0 exp 0000000000000000 cur 1317994930 last 0
# Lustre: 31793:0:(ldlm_lib.c:877:target_handle_connect()) MGS:            connection from e5232e74-1e61-fad1-b59b-6e4a7d674016@192.168.122.218@tcp t0 exp 0000000000000000 cur 1317994928 last 0
def client_connection_handler(message, host):
    sev = logging.INFO
    # get the client NID out of the string
    nid_start = message.find("@") + 1
    nid_len = message[nid_start:].find(" ")
    # and the UUID
    uuid_start = message.find(" from ") + 5
    uuid_len = message[uuid_start:].find("@")
    # and of course the target
    target_end = message.find(": connection from") - 1
    target_start = message[:target_end].rfind(" ") + 1
    msg = "client %s from %s connected to target %s" % (
        message[uuid_start : uuid_start + uuid_len],
        message[nid_start : nid_start + nid_len],
        message[target_start:target_end],
    )
    lustre_pid = message[9 : 9 + message[9:].find(":")]

    ClientConnectEvent.register_event(severity=sev, alert_item=host, message_str=msg, lustre_pid=lustre_pid)


#
# Lustre: 5629:0:(sec.c:1474:sptlrpc_import_sec_adapt()) import lustre-MDT0000->NET_0x20000c0a87ada_UUID netid 20000: select flavor null
# Lustre: 20380:0:(sec.c:1474:sptlrpc_import_sec_adapt()) import MGC192.168.122.105@tcp->MGC192.168.122.105@tcp_0 netid 20000: select flavor null
#
def server_security_flavor_handler(message, host):
    # get the flavour out of the string
    flavour_start = message.rfind(" ") + 1
    flavour = message[flavour_start:]
    lustre_pid = message[9 : 9 + message[9:].find(":")]

    # Associate this with a previous client connect event if possible
    try:
        event = ClientConnectEvent.objects.filter(lustre_pid=lustre_pid).order_by("-id")[0]
        event.message_str = "%s with security flavor %s" % (event.message_str, flavour)
        event.save()
    except IndexError:
        pass


#
# client evicted by the admin:
#
# Lustre: 2689:0:(genops.c:1379:obd_export_evict_by_uuid()) lustre-OST0001: evicting 26959b68-1208-1fca-1f07-da2dc872c55f at adminstrative request
#
def admin_client_eviction_handler(message, host):
    uuid = _get_word_after(message, "evicting ")
    msg = "client %s evicted by the administrator" % uuid
    lustre_pid = message[9 : 9 + message[9:].find(":")]
    ClientConnectEvent.register_event(severity=logging.WARNING, alert_item=host, message_str=msg, lustre_pid=lustre_pid)


#
# real eviction
#
# LustreError: 0:0:(ldlm_lockd.c:356:waiting_locks_callback()) ### lock callback timer expired after 101s: evicting client at 0@lo ns: mdt-ffff8801cd5be000 lock: ffff880126f8f480/0xe99a593b682aed45 lrc: 3/0,0 mode: PR/PR res: 8589935876/10593 bits 0x3 rrc: 2 type: IBT flags: 0x4000020 remote: 0xe99a593b682aecea expref: 14 pid: 3636 timeout: 4389324308'
def client_eviction_handler(message, host):
    s = message.find("### ") + 4
    l = message[s:].find(": evicting client at ")
    reason = message[s : s + l]
    client = _get_word_after(message, ": evicting client at ")
    msg = "client %s evicted: %s" % (client, reason)
    lustre_pid = _get_word_after(message, "pid: ")
    ClientConnectEvent.register_event(severity=logging.WARNING, alert_item=host, message_str=msg, lustre_pid=lustre_pid)


class LogMessageParser(object):
    selectors = {
        "Can't start acceptor on port": port_used_handler,
        "Can't create socket:": port_used_handler,
        ": connection from ": client_connection_handler,
        ": select flavor ": server_security_flavor_handler,
        ": obd_export_evict_by_uuid()": admin_client_eviction_handler,
        ": evicting client at ": client_eviction_handler,
    }

    def __init__(self):
        self._hosts = {}

    # FIXME: need to update this cache of hosts when a host is removed
    def get_host(self, fqdn):
        try:
            return self._hosts[fqdn]
        except KeyError:
            try:
                host = ManagedHost.objects.get(fqdn=fqdn)
                self._hosts[fqdn] = host
                return host
            except ManagedHost.DoesNotExist:
                return None

    def parse(self, fqdn, message):
        hit = find_one_in_many(message["message"], self.selectors.keys())
        if hit:
            h = self.get_host(fqdn)
            if h is None:
                return

            fn = self.selectors[hit]
            with transaction.commit_manually():
                try:
                    fn(message["message"], h)
                except Exception as e:
                    syslog_events_log.error(
                        "Failed to parse log line '%s' using handler %s: %s" % (message["message"], fn, e)
                    )
                    transaction.rollback()
                else:
                    transaction.commit()
