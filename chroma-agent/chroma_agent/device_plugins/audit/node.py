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


import re
import socket
from chroma_agent.device_plugins.audit import BaseAudit
from chroma_agent.device_plugins.audit.mixins import FileSystemMixin


class NodeAudit(BaseAudit, FileSystemMixin):
    def __init__(self, **kwargs):
        super(NodeAudit, self).__init__(**kwargs)

        self.raw_metrics['node'] = {}

    def parse_meminfo(self):
        """Returns a dict representation of /proc/meminfo"""
        return dict((k, int(re.sub('[^\d]*', '', v))) for k, v in
                    [re.split(':\s+', line) for line in
                        self.read_lines('/proc/meminfo')])

    def parse_cpustats(self):
        """Reads the first string of /proc/stat and returns a dict
        containing used/total cpu slices."""
        cpu_str = self.read_string('/proc/stat')
        slices = [int(val) for val in re.split('\s+', cpu_str)[1:]]
                                # 2.6+
                                                      # 2.6.11+
                                                             # 2.6.24+
        # usr, nice, sys, idle, iowait, irq, softirq, steal, guest
        # steal seems to only be used on s390; we can ignore it
        # guest is included in user, so we shouldn't double-count it
        total = sum(slices[0:6])
        user = sum(slices[0:1])
        system = slices[2] + sum(slices[5:6])
        idle = slices[3]
        iowait = slices[4]
        return {'user': user, 'system': system, 'idle': idle, 'iowait': iowait, 'total': total}

    def _gather_raw_metrics(self):
        self.raw_metrics['node']['hostname'] = socket.gethostname()
        self.raw_metrics['node']['meminfo'] = self.parse_meminfo()
        self.raw_metrics['node']['cpustats'] = self.parse_cpustats()

    def metrics(self):
        """Returns a hash of metric values."""
        self._gather_raw_metrics()
        return {"raw": self.raw_metrics}
