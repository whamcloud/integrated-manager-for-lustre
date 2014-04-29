#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2014 Intel Corporation All Rights Reserved.
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


import traceback
from django import db
from django.utils import dateparse
from chroma_core.models import Stats
from chroma_core.services import ChromaService, log_register, queue


log = log_register(__name__)


class StatsQueue(queue.ServiceQueue):
    name = 'stats'

    def put(self, samples):
        queue.ServiceQueue.put(self, [(id, str(dt), value) for id, dt, value in samples])


class Service(ChromaService):
    def run(self):
        self.queue = StatsQueue()
        self.queue.purge()
        self.queue.serve(callback=self.insert)

    def insert(self, samples):
        try:
            outdated = Stats.insert((id, dateparse.parse_datetime(dt), value) for id, dt, value in samples)
        except db.IntegrityError:
            log.error("Duplicate stats insert: " + db.connection.queries[-1]['sql'])
            db.transaction.rollback()  # allow future stats to still work
        except:
            log.error("Error handling stats insert: " + traceback.format_exc())
        else:
            if outdated:
                log.warn("Outdated samples ignored: {0}".format(outdated))

    def stop(self):
        self.queue.stop()
