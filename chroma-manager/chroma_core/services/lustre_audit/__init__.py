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


import traceback
import sys
from chroma_core.services.lustre_audit.update_scan import UpdateScan
from chroma_core.models import ManagedHost
from chroma_core.services import ChromaService, log_register
from chroma_core.services.queue import AgentRxQueue
from django.db import transaction


log = log_register(__name__)


class Service(ChromaService):
    PLUGIN_NAME = 'lustre'

    def __init__(self):
        self._queue = AgentRxQueue(Service.PLUGIN_NAME)
        self._queue.purge()

    def run(self):
        self._queue.serve(data_callback = self.on_data)

    def on_data(self, fqdn, data):
        with transaction.commit_manually():
            transaction.commit()

        try:
            host = ManagedHost.objects.get(fqdn = fqdn)
            UpdateScan().run(host.id, data)
        except Exception:
            log.error("Error handling lustre message: %s", '\n'.join(traceback.format_exception(*(sys.exc_info()))))

    def stop(self):
        self._queue.stop()
