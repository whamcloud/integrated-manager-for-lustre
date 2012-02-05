#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

import settings

from chroma_core.models import SyslogEvent, ClientConnectEvent, Systemevents
from django.db import transaction

import logging
import re

syslog_events_log = settings.setup_log('syslog_events')

_re_cache = {}


def re_find_one_in_many(haystack, needles):
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


def plain_find_one_in_many(haystack, needles):
    for n in needles:
        if haystack.find(n) != -1:
            return n

# use the plain version for now
# in the future, we can switch to REs or a combination
find_one_in_many = plain_find_one_in_many


#
# acceptor port is already being used
#
# LustreError: 122-1: Can't start acceptor on port 988: port already in use
def port_used_handler(entry, h):
    SyslogEvent(severity = logging.ERROR, host = h,
                message_str = "Lustre port already being used").save()


#
# client connected to services:
#
# Lustre: 5629:0:(ldlm_lib.c:877:target_handle_connect()) lustre-MDT0000: connection from 26959b68-1208-1fca-1f07-da2dc872c55f@192.168.122.218@tcp t0 exp 0000000000000000 cur 1317994929 last 0
# Lustre: 27559:0:(ldlm_lib.c:871:target_handle_connect()) lustre-OST0001: connection from 26959b68-1208-1fca-1f07-da2dc872c55f@192.168.122.218@tcp t0 exp 0000000000000000 cur 1317994930 last 0
# Lustre: 9150:0:(ldlm_lib.c:871:target_handle_connect()) lustre-OST0000: connection from 26959b68-1208-1fca-1f07-da2dc872c55f@192.168.122.218@tcp t0 exp 0000000000000000 cur 1317994930 last 0
# Lustre: 31793:0:(ldlm_lib.c:877:target_handle_connect()) MGS:            connection from e5232e74-1e61-fad1-b59b-6e4a7d674016@192.168.122.218@tcp t0 exp 0000000000000000 cur 1317994928 last 0
def client_connection_handler(entry, h):
    sev = logging.INFO
    # get the client NID out of the string
    nid_start = entry.message.find("@") + 1
    nid_len = entry.message[nid_start:].find(" ")
    # and the UUID
    uuid_start = entry.message.find(" from ") + 5
    uuid_len = entry.message[uuid_start:].find("@")
    # and of course the target
    target_end = entry.message.find(": connection from") - 1
    target_start = entry.message[:target_end].rfind(" ") + 1
    msg = "client %s from %s connected to target %s" % \
        (entry.message[uuid_start:uuid_start + uuid_len],
         entry.message[nid_start:nid_start + nid_len],
         entry.message[target_start:target_end])
    lustre_pid = entry.message[9:9 + \
                               entry.message[9:].find(":")]

    ClientConnectEvent(severity = sev, host = h, message_str = msg,
                       lustre_pid = lustre_pid).save()


#
# Lustre: 5629:0:(sec.c:1474:sptlrpc_import_sec_adapt()) import lustre-MDT0000->NET_0x20000c0a87ada_UUID netid 20000: select flavor null
#
def server_security_flavor_handler(entry, h):
    # get the flavour out of the string
    flavour_start = entry.message.rfind(" ") + 1
    flavour = entry.message[flavour_start:]
    lustre_pid = entry.message[9:9 + \
                               entry.message[9:].find(":")]
    event = ClientConnectEvent.objects.filter(lustre_pid = \
                             lustre_pid).order_by('-id')[0]
    event.message_str = "%s with security flavor %s" % \
                        (event.message_str, flavour)
    event.save()


#
# client evicted by the admin:
#
# Lustre: 2689:0:(genops.c:1379:obd_export_evict_by_uuid()) lustre-OST0001: evicting 26959b68-1208-1fca-1f07-da2dc872c55f at adminstrative request
#
def client_eviction_handler(entry, h):
    # get the client UUID out of the string
    uuid_start = entry.message.find("evicting ") + 9
    uuid_len = entry.message[uuid_start:].find(" ")
    msg = "client %s evicted by the administrator" % \
        entry.message[uuid_start:uuid_start + uuid_len]
    lustre_pid = entry.message[9:9 + \
                               entry.message[9:].find(":")]
    ClientConnectEvent(severity = logging.WARNING, host = h, message_str = msg,
                       lustre_pid = lustre_pid).save()


class SystemEventsAudit:
    def get_last_id(self):
        from chroma_core.models import LastSystemeventsProcessed
        l, c = LastSystemeventsProcessed.objects.get_or_create(id__gt = 0)
        return l.last

    def store_last_id(self, last):
        from chroma_core.models import LastSystemeventsProcessed
        l = LastSystemeventsProcessed.objects.get()
        l.last = last
        l.save()

    selectors = {"Can't start acceptor on port": port_used_handler,
                 "Can't create socket:": port_used_handler,
                 ": connection from ": client_connection_handler,
                 ": select flavor ": server_security_flavor_handler,
                 ": evicting ": client_eviction_handler,
                }

    def parse_log_entries(self):
        from chroma_core.models import ManagedHost

        trans_size = 100
        with transaction.commit_on_success():
            def get_host_from_entry(entry):
                try:
                    h = hosts[entry.fromhost]
                except KeyError:
                    try:
                        h = ManagedHost.objects.get(fqdn = entry.fromhost)
                        hosts[entry.fromhost] = h
                    except ManagedHost.DoesNotExist:
                        h = None

                return h

            # a cache for the Hosts
            hosts = {}

            while True:
                new_entries = Systemevents.objects.filter(id__gt = \
                                                      self.get_last_id()).\
                                                    order_by('id')[:trans_size]

                for entry in new_entries:
                    hit = find_one_in_many(entry.message, self.selectors.keys())
                    if hit:
                        h = get_host_from_entry(entry)
                        if h != None:
                            fn = self.selectors[hit]
                            try:
                                fn(entry, h)
                            except Exception, e:
                                syslog_events_log.error("Failed to parse log line %s using handler %s: %s" % (entry.message, fn, e))
                    # now that we have some real events, i don't think we
                    # need to keep logging this noise, but let's leave it
                    # here in case somebody wants to
                    #elif entry.message.find("LustreError:") > 0:
                    #    sev = ERROR
                    #    msg = entry.message
                    #    h = get_host_from_entry(entry)
                    #
                    #    if h != None:
                    #        SyslogEvent(severity = sev,
                    #                    host = ManagedHost.objects.get(address = h),
                    #                    message_str = msg).save()
                    #elif entry.message.find("Lustre:") > 0:
                    #    sev = INFO
                    #    msg = entry.message
                    #    h = get_host_from_entry(entry)
                    #
                    #    if h != None:
                    #        SyslogEvent(severity = sev,
                    #                    host = ManagedHost.objects.get(address = h),
                    #                    message_str = msg).save()

                if new_entries.count() > 0:
                    self.store_last_id(new_entries[new_entries.count() - 1].id)

                # less than trans_size records returned means we got the
                # last bunch
                if new_entries.count() < trans_size:
                    break
