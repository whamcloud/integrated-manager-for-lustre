#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2015 Intel Corporation All Rights Reserved.
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


import time
import sys
from threading import Thread

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from chroma_core.lib import util

is_job_scheduler = ('job_scheduler' in sys.argv)


class DatabaseChangedThread(Thread):
    threads = {}

    def __init__(self, timestamp, tablename):
        super(DatabaseChangedThread, self).__init__()
        self.timestamp = timestamp
        self.tablename = tablename
        self.threads[self] = {'table': tablename}

    def run(self):
        from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
        JobSchedulerClient.table_change(self.timestamp, self.tablename)
        del self.threads[self]


@receiver(post_save)
@receiver(post_delete)
def database_changed(sender, **kwargs):
    if sender._meta.db_table.startswith('chroma_core'):     # We are only interested in our tables, not the django ones.
        try:
            timestamp = int(time.time() * util.SECONDSTOMICROSECONDS)
            table_name = sender._meta.db_table

            if is_job_scheduler:
                import long_polling
                long_polling.table_change(timestamp, table_name)
            else:
                DatabaseChangedThread(timestamp, table_name).start()
        except Exception:
            pass
