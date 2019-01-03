# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import os
import dse

from django.db import transaction

from chroma_core.services.syslog.parser import LogMessageParser
from chroma_core.models.log import LogMessage
from chroma_core.services import ChromaService, log_register
from chroma_core.services.queue import AgentRxQueue
from iml_common.lib.date_time import IMLDateTime

import settings


log = log_register("systemd_journal")


class Service(ChromaService):
    PLUGIN_NAME = "systemd_journal"

    def __init__(self):
        super(Service, self).__init__()
        self._queue = AgentRxQueue(Service.PLUGIN_NAME)
        self._queue.purge()
        self._table_size = LogMessage.objects.count()
        self._parser = LogMessageParser()

        dse.patch_models()

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
                    removed_entries = LogMessage.objects.all().order_by("id")[0:trans_size]
                    self.log.debug("writing %s batch of entries" % trans_size)
                    try:
                        f = open(overflow_filename, "a")
                        for line in removed_entries:
                            f.write("%s\n" % line.__str__())
                        LogMessage.objects.filter(id__lte=removed_entries[-1].id).delete()
                    except Exception as e:
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

    def on_data(self, fqdn, body):
        with transaction.commit_on_success():
            with LogMessage.delayed as log_messages:
                for msg in body["log_lines"]:
                    try:
                        log_messages.insert(
                            dict(
                                fqdn=fqdn,
                                message=msg["message"],
                                severity=msg["severity"],
                                facility=msg["facility"],
                                tag=msg["source"],
                                datetime=IMLDateTime.parse(msg["datetime"]).as_datetime,
                                message_class=LogMessage.get_message_class(msg["message"]),
                            )
                        )
                        self._table_size += 1

                        self._parser.parse(fqdn, msg)
                    except Exception as e:
                        self.log.error("Error %s ingesting systemd-journal entry: %s" % (e, msg))

    def run(self):
        super(Service, self).run()

        self._queue.serve(data_callback=self.on_data)

    def stop(self):
        super(Service, self).stop()

        self._queue.stop()
