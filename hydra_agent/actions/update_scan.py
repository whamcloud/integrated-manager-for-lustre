# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

import os
import glob

from utils import Mounts, normalize_device
from hydra_agent.actions.targets import get_resource_locations
from hydra_agent.actions.lnet_scan import lnet_status
from hydra_agent import shell
from hydra_agent.plugins import AgentPlugin

# FIXME: weird naming, 'LocalAudit' is the class that fetches stats
from hydra_agent.audit.local import LocalAudit


def update_scan(args = None):
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

    return {
            "metrics": metrics,
            "lnet_loaded": lnet_loaded,
            "lnet_up": lnet_up,
            "mounts": mounts,
            "resource_locations": get_resource_locations()
            }


class UpdateScanPlugin(AgentPlugin):
    def register_commands(self, parser):
        p = parser.add_parser("update-scan",
                              help="scan for updates to monitored filesystems")
        p.set_defaults(func=update_scan)
