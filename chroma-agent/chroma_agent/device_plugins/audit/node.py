# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import re
import socket
import platform

from chroma_agent.lib.shell import AgentShell
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

    def properties(self):
        """Returns less volatile node data suitable for host validation.

        If the fetched property is expensive to compute, it should be cached / updated less frequently.
        """
        zfs_not_installed, stdout, stderr = AgentShell.run_old(['which', 'zfs'])

        return {'zfs_installed': not zfs_not_installed,
                'distro': platform.linux_distribution()[0],
                'distro_version': float('.'.join(platform.linux_distribution()[1].split('.')[:2])),
                'python_version_major_minor': float("%s.%s" % (platform.python_version_tuple()[0],
                                                               platform.python_version_tuple()[1])),
                'python_patchlevel': int(platform.python_version_tuple()[2]),
                'kernel_version': platform.release()}
