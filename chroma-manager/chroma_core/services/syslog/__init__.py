#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import dateutil.parser
import os

from chroma_core.services.syslog.parser import LogMessageParser
from chroma_core.models.log import LogMessage
from chroma_core.services import ChromaService
from chroma_core.services.queue import ServiceQueue

from django.db import transaction
import settings


SYSLOG_PLUGIN_NAME = 'syslog'


class SyslogRxQueue(ServiceQueue):
    # FIXME: queue named by convention, document it or wrap it in a function
    name = 'agent_%s_rx' % SYSLOG_PLUGIN_NAME


class Service(ChromaService):
    def __init__(self):
        super(Service, self).__init__()
        self._queue = SyslogRxQueue()
        self._table_size = LogMessage.objects.count()
        self._parser = LogMessageParser()

    def _check_size(self):
        """Apply a size limit to the table of log messages"""
        MAX_ROWS_PER_TRANSACTION = 10000
        removed_num_entries = 0
        overflow_filename = os.path.join(settings.LOG_PATH, "db_log")

        if self._table_size > settings.DBLOG_HW:
            remove_num_entries = self._table_size - settings.DBLOG_LW

            trans_size = min(MAX_ROWS_PER_TRANSACTION, remove_num_entries)
            with transaction.commit_on_success():
                while remove_num_entries > 0:
                    removed_entries = LogMessage.objects.all().order_by('id')[0:trans_size]
                    self.log.debug("writing %s batch of entries" % trans_size)
                    try:
                        f = open(overflow_filename, "a")
                        for line in removed_entries:
                            f.write("%s\n" % line.__str__())
                        LogMessage.objects.filter(id__lte = removed_entries[-1].id).delete()
                    except Exception, e:
                        self.log.error("error opening/writing/closing the db_log: %s" % e)
                    finally:
                        f.close()

                    remove_num_entries -= trans_size
                    removed_num_entries += trans_size
                    if remove_num_entries < trans_size:
                        trans_size = remove_num_entries

        self._table_size -= removed_num_entries
        self.log.info("Wrote %s DB log entries to %s" % (removed_num_entries, overflow_filename))

        return removed_num_entries

    def on_message(self, message):
        fqdn = message['fqdn']

        # FIXME: message['body'] assumes this class knows the agent comms
        # message format
        # -- better to pass services a Message class instance with a body member
        # (they do need the rest of the envelope too sometimes, e.g. for agent_rpc, but
        #  this simple case of consuming bodies should be made simple)
        for msg in message['body']['messages']:
            try:
                log_message = LogMessage.objects.create(
                    fqdn = fqdn,
                    message = msg['message'],
                    severity = msg['severity'],
                    facility = msg['facility'],
                    tag = msg['source'],
                    datetime = dateutil.parser.parse(msg['datetime']))

                self._parser.parse(log_message)
                self._table_size += 1
            except Exception, e:
                self.log.error("Error %s parsing syslog entry: %s" % (e, msg))

    def run(self):
        self._queue.serve(self.on_message)

    def stop(self):
        self._queue.stop()
