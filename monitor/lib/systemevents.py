#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.core.management import setup_environ
import settings

# Access to 'monitor' database
from monitor.models import *
from django.db import transaction

import re

class SystemEventsAudit:
    from monitor.models import LastSystemeventsProcessed
    def get_last_id(self):
        l, c = LastSystemeventsProcessed.objects.get_or_create(id__gt = 0)
        return l.last

    def store_last_id(self, last):
        l = LastSystemeventsProcessed.objects.get()
        l.last = last
        l.save()

    def parse_log_entries(self):
        from logging import INFO, ERROR
        from monitor.models import Host

        trans_size = 100
        with transaction.commit_on_success():
            # a cache for the Hosts
            hosts = {}
            while True:
                new_entries = Systemevents.objects.filter(id__gt = \
                                                      self.get_last_id()).\
                                                    order_by('id')[:trans_size]

                for entry in new_entries:
                    is_event = False
                    if entry.message.find("LustreError:") > 0:
                        sev = ERROR
                        is_event = True
                    elif entry.message.find("Lustre:") > 0:
                        sev = INFO
                        is_event = True

                    if is_event:
                        msg = entry.message
                        try:
                            h = hosts[entry.fromhost]
                        except KeyError:
                            try:
                                h = Host.objects.get(address = entry.fromhost)
                                hosts[entry.fromhost] = h
                            except Host.DoesNotExist:
                                h = None

                        if h != None:
                            SyslogEvent(severity = sev,
                                        host = Host.objects.get(address = \
                                                                entry.fromhost),
                                        message_str = msg).save()

                if new_entries.count() > 0:
                    self.store_last_id(new_entries[new_entries.count() - 1].id)

                # less than trans_size records returned means we got the
                # last bunch
                if new_entries.count() < trans_size:
                    break
