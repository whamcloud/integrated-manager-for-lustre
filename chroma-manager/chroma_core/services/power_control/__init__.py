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


import threading
from chroma_core.services import ChromaService, ServiceThread


class Service(ChromaService):
    def __init__(self):
        super(Service, self).__init__()
        self.threads = []
        self._complete = threading.Event()

    def run(self):
        from chroma_core.services.power_control.manager import PowerControlManager
        from chroma_core.services.power_control.monitor_daemon import PowerMonitorDaemon
        from chroma_core.services.power_control.rpc import PowerControlRpc

        manager = PowerControlManager()
        monitor_daemon = PowerMonitorDaemon(manager)

        self._rpc_thread = ServiceThread(PowerControlRpc(manager))
        self._monitor_daemon_thread = ServiceThread(monitor_daemon)

        self._rpc_thread.start()
        self._monitor_daemon_thread.start()

        self._complete.wait()

    def stop(self):
        self.log.info("Stopping...")
        self._rpc_thread.stop()
        self._monitor_daemon_thread.stop()

        self.log.info("Joining...")
        self._rpc_thread.join()
        self._monitor_daemon_thread.join()

        self.log.info("Complete.")

        self._complete.set()
