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


import glob
import os
import re

from chroma_agent.lib.shell import AgentShell
from chroma_agent.log import console_log
from chroma_agent.device_plugins.linux_components.device_helper import DeviceHelper
from chroma_agent.chroma_common.lib.exception_sandbox import exceptionSandBox


class EMCPower(DeviceHelper):
    """Reads /dev/emcpower?*"""

    def __init__(self, block_devices):
        self.emcpowers = self._composite_device_list(self._get_emcpower())

    def all(self):
        return self.emcpowers

    @exceptionSandBox(console_log, [])
    def _get_emcpower(self):
        try:
            devs = []

            # We are looking in /dev for all emcpowerX devices but not /dev/emcpower. The *? means we get /dev/emcpowerX
            # and /dev/emcpowerXX in case they have more than 26 devices
            for device_path in glob.glob("/dev/emcpower?*"):
                try:
                    device_major_minor = self._dev_major_minor(device_path)

                    name = os.path.basename(device_path)

                    out = AgentShell.try_run(['powermt', 'display', 'dev=%s' % name])

                    # The command above returns something like below, so use the === lines as keys to search for different things.
                    # above search for the logical device ID and below search for the devices used by the emcpower device.

                    # VNX ID=APM00122204204 [NGS1]\n"
                    # Logical device ID=600601603BC12D00C4CECB092F1FE311 [LUN 11]\n"
                    # state=alive; policy=CLAROpt; queued-IOs=0
                    # Owner: default=SP A, current=SP A	Array failover mode: 4
                    # ==============================================================================
                    # --------------- Host ---------------   - Stor -  -- I/O Path --   -- Stats ---
                    # ###  HW Path               I/O Paths    Interf.  Mode     State   Q-IOs Errors
                    # ==============================================================================
                    #  13 qla2xxx                sdb         SP A0    active   alive      0      0"
                    #  12 qla2xxx                sde         SP B0    active   alive      0      0

                    pwr_lines = [i for i in out.split("\n") if len(i) > 0]

                    device_list = []

                    # Compose a lookup of names of multipath devices, for use parsing other lines
                    headerlinesremaining = 2                # pass 2 ========= type lines.

                    for line in pwr_lines:
                        if (headerlinesremaining > 0):
                            if line.startswith("================="):
                                headerlinesremaining -= 1

                            match = re.search("Logical device ID=([0-9A-Z]+)", line)
                            if match:
                                device_uuid = match.group(1)
                        else:
                            tokens = re.findall(r"[\w]+", line)

                            device_list.append("/dev/%s" % tokens[2])

                    devs.append({
                        "uuid": device_uuid[0:8] + ":" + device_uuid[8:16] + ":" + device_uuid[16:24] + ":" + device_uuid[24:32],
                        "path": device_path,
                        "mm": device_major_minor,
                        "device_paths": device_list
                        })
                except OSError as os_error:
                    # powermt doesn't exist, threw an error etc.
                    console_log.debug("powermt threw an exception '%s' " % os_error.strerror)

            return devs
        except IOError:
            return []
