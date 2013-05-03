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


from collections import defaultdict
import os
import glob
import datetime

from chroma_agent.utils import Mounts, normalize_device
from chroma_agent.action_plugins.lnet_scan import lnet_status, get_nids
from chroma_agent import shell, version
from chroma_agent.plugin_manager import DevicePlugin, ActionPluginManager

# FIXME: weird naming, 'LocalAudit' is the class that fetches stats
from chroma_agent.device_plugins.audit.local import LocalAudit


class LustrePlugin(DevicePlugin):
    def _scan_mounts(self):
        mounts = {}

        for device, mntpnt, fstype in Mounts().all():
            if fstype != 'lustre':
                continue

            if not os.path.exists(device):
                continue

            # Assume that while a filesystem is mounted, its UUID and LABEL don't change.
            # Therefore we can avoid repeated blkid calls with a little caching.
            if device in self._mount_cache:
                fs_uuid = self._mount_cache[device]['fs_uuid']
                fs_label = self._mount_cache[device]['fs_label']
            else:
                self._mount_cache[device]['fs_uuid'] = fs_uuid = shell.try_run(["blkid", "-o", "value", "-s", "UUID", device]).strip()
                self._mount_cache[device]['fs_label'] = fs_label = shell.try_run(["blkid", "-o", "value", "-s", "LABEL", device]).strip()

            dev_normalized = normalize_device(device)

            recovery_status = {}
            try:
                recovery_file = glob.glob("/proc/fs/lustre/*/%s/recovery_status" % fs_label)[0]
                recovery_status_text = open(recovery_file).read()
                for line in recovery_status_text.split("\n"):
                    tokens = line.split(":")
                    if len(tokens) != 2:
                        continue
                    k = tokens[0].strip()
                    v = tokens[1].strip()
                    recovery_status[k] = v
            except IndexError:
                # If the recovery_status file doesn't exist,
                # we will return an empty dict for recovery info
                pass

            mounts[device] = {
                'device': dev_normalized,
                'fs_uuid': fs_uuid,
                'mount_point': mntpnt,
                'recovery_status': recovery_status
            }

        # Drop cached info about anything that is no longer mounted
        for k in self._mount_cache.keys():
            if not k in mounts:
                del self._mount_cache[k]

        return mounts.values()

    def _scan(self):
        started_at = datetime.datetime.utcnow().isoformat() + "Z"

        metrics = LocalAudit().metrics()
        lnet_loaded, lnet_up = lnet_status()
        if lnet_up:
            lnet_nids = get_nids()
        else:
            lnet_nids = None

        # Only set resource_locations if we have the management package
        try:
            from chroma_agent.action_plugins.manage_targets import get_resource_locations
            resource_locations = get_resource_locations()
        except ImportError:
            resource_locations = None

        mounts = self._scan_mounts()

        # FIXME: HYD-1095 we should be sending a delta instead of a full dump every time
        return {
            "started_at": started_at,
            "agent_version": version(),
            "capabilities": ActionPluginManager().capabilities,
            "metrics": metrics,
            "lnet_loaded": lnet_loaded,
            "lnet_nids": lnet_nids,
            "lnet_up": lnet_up,
            "mounts": mounts,
            "resource_locations": resource_locations
        }

    def start_session(self):
        self._mount_cache = defaultdict(dict)

        return self._scan()

    def update_session(self):
        return self._scan()
