# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import re
import os

from chroma_agent.lib.shell import AgentShell
from chroma_agent.log import console_log
from iml_common.lib.exception_sandbox import exceptionSandBox


class MdRaid(object):
    """ Reads /proc/mdstat """
    MDRAIDPATH = os.path.join('/dev', 'md')

    def __init__(self, block_devices):
        self.block_devices = block_devices
        self.mds = self.block_devices.composite_device_list(self._get_md())

    def all(self):
        return self.mds

    @exceptionSandBox(console_log, [])
    def _get_md(self):
        try:
            matches = re.finditer(
                "^(md\d+) : active",
                open('/proc/mdstat').read().strip(),
                flags=re.MULTILINE)
            dev_md_nodes = self.block_devices.find_block_devs(self.MDRAIDPATH)

            devs = []
            for match in matches:
                # e.g. md0
                device_name = match.group(1)
                device_path = "/dev/%s" % device_name
                device_major_minor = self.block_devices.path_to_major_minor(
                    device_path)

                # Defensive, but perhaps the md device doesn't show up as disk/by-id in which case we can't use it
                try:
                    device_path = dev_md_nodes[device_major_minor]
                except KeyError:
                    continue

                try:
                    detail = AgentShell.try_run([
                        'mdadm', '--brief', '--detail', '--verbose',
                        device_path
                    ])
                    device_uuid = re.search(
                        "UUID=(.*)[ \\n]", detail.strip(),
                        flags=re.MULTILINE).group(1)
                    device_list_csv = re.search(
                        "^\s+devices=(.*)$",
                        detail.strip(),
                        flags=re.MULTILINE).group(1)
                    device_list = device_list_csv.split(",")

                    devs.append({
                        "uuid": device_uuid,
                        "path": device_path,
                        "mm": device_major_minor,
                        "device_paths": device_list
                    })
                except OSError as os_error:
                    # mdadm doesn't exist, threw an error etc.
                    console_log.debug(
                        "mdadm threw an exception '%s' " % os_error.strerror)

            return devs
        except IOError:
            return []
