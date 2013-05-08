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


"""
Dev/test benchmarking tool for the RPC subsystem.
"""

import threading
import time

from chroma_core.services import ChromaService
from chroma_core.services.pinger import PingServerRpcInterface
from chroma_core.services.rpc import RpcTimeout


class Pinger(threading.Thread):
    def __init__(self, payload):
        super(Pinger, self).__init__()
        self.timed_out = False
        self.error = False
        self.latency = None
        self._payload = payload

    def run(self):
        ts = time.time()
        try:
            output = PingServerRpcInterface().ping(self._payload)
            assert self._payload == output
        except RpcTimeout:
            self.timed_out = True
        except Exception:
            self.error = True
        else:
            te = time.time()
            self.latency = te - ts


class Service(ChromaService):
    def run(self):
        overall_ts = time.time()
        threads = []
        N = 4096

        for i in range(0, N):
            thread = Pinger(i)
            thread.start()
            threads.append(thread)

        tot_latency = 0.0
        timeout_count = 0
        error_count = 0
        for i, thread in enumerate(threads):
            thread.join()
            if thread.timed_out:
                timeout_count += 1
            elif thread.error:
                error_count += 1
            else:
                latency = thread.latency
                tot_latency += latency
        overall_te = time.time()

        print "%.4d/%.4d/%.4d %10.1f %10.2fms" % (N - timeout_count - error_count, timeout_count, error_count, N / (overall_te - overall_ts), (tot_latency / N) * 1000.0)

        #print "Successful/timeout/error: %s/%s/%s" % (N - timeout_count - error_count, timeout_count, error_count)
        #print "Issue rate: %s/s" % (N / (overall_te - overall_ts))
        #print "Avg RTT: %.2fms" % ((tot_latency / N) * 1000.0)
        import os
        os._exit(0)

    def stop(self):
        pass
