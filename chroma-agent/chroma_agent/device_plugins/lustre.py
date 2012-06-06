#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import os
import glob
import datetime

from chroma_agent.utils import Mounts, normalize_device, list_capabilities
from chroma_agent.action_plugins.lnet_scan import lnet_status, get_nids
from chroma_agent import shell, version
from chroma_agent.plugins import DevicePlugin

# FIXME: weird naming, 'LocalAudit' is the class that fetches stats
from chroma_agent.audit.local import LocalAudit


def update_scan(args = None):
    started_at = datetime.datetime.utcnow().isoformat() + "Z"
    mounts = []
    for device, mntpnt, fstype in Mounts().all():
        if fstype != 'lustre':
            continue

        if not os.path.exists(device):
            continue

        fs_uuid = shell.try_run(["blkid", "-o", "value", "-s", "UUID", device]).strip()
        fs_label = shell.try_run(["blkid", "-o", "value", "-s", "LABEL", device]).strip()
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

        mounts.append({
            'device': dev_normalized,
            'fs_uuid': fs_uuid,
            'mount_point': mntpnt,
            'recovery_status': recovery_status
            })

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

    # FIXME: HYD-1095 we should be sending a delta instead of a full dump every time
    return {
            "started_at": started_at,
            "agent_version": version(),
            "capabilities": list_capabilities(),
            "metrics": metrics,
            "lnet_loaded": lnet_loaded,
            "lnet_nids": lnet_nids,
            "lnet_up": lnet_up,
            "mounts": mounts,
            "resource_locations": resource_locations
            }


class UpdateScanPlugin(DevicePlugin):
    def start_session(self):
        return update_scan()

    def update_session(self):
        return update_scan()
