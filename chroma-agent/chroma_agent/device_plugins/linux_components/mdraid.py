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

from chroma_agent.chroma_common.lib import shell
from chroma_agent.log import console_log
from chroma_agent.device_plugins.linux_components.device_helper import DeviceHelper
from chroma_agent.chroma_common.lib.exception_sandbox import exceptionSandBox


class MdRaid(DeviceHelper):
    """Reads /proc/mdstat"""

    def __init__(self, block_devices):
        self.mds = self._composite_device_list(self._get_md())

    def all(self):
        return self.mds

    @exceptionSandBox(console_log, [])
    def _get_md(self):
        try:
            matches = re.finditer("^(md\d+) : active", open('/proc/mdstat').read().strip(), flags = re.MULTILINE)
            dev_md_nodes = self._find_block_devs(self.MDRAIDPATH)

            devs = []
            for match in matches:
                # e.g. md0
                device_name = match.group(1)
                device_path = "/dev/%s" % device_name
                device_major_minor = self._dev_major_minor(device_path)

                # Defensive, but perhaps the md device doesn't show up as disk/by-id in which case we can't use it
                try:
                    device_path = dev_md_nodes[device_major_minor]
                except KeyError:
                    continue

                try:
                    detail = shell.try_run(['mdadm', '--brief', '--detail', '--verbose', device_path])
                    device_uuid = re.search("UUID=(.*)[ \\n]", detail.strip(), flags = re.MULTILINE).group(1)
                    device_list_csv = re.search("^\s+devices=(.*)$", detail.strip(), flags = re.MULTILINE).group(1)
                    device_list = device_list_csv.split(",")

                    devs.append({
                        "uuid": device_uuid,
                        "path": device_path,
                        "mm": device_major_minor,
                        "device_paths": device_list
                        })
                except OSError as os_error:
                    # mdadm doesn't exist, threw an error etc.
                    console_log.debug("mdadm threw an exception '%s' " % os_error.strerror)

            return devs
        except IOError:
            return []
