#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from chroma_agent.plugins import ActionPlugin
import os


def lnet_status():
    lnet_loaded = False
    for module_line in open("/proc/modules").readlines():
        if module_line.startswith("lnet "):
            lnet_loaded = True
            break

    lnet_up = os.path.exists("/proc/sys/lnet/stats")

    return lnet_loaded, lnet_up


def lnet_scan(args):
    """Parse /proc for running LNet NIDs, and return a 2-tuple of
       (whether lnet is up, list of NID strings)"""

    lnet_loaded, lnet_up = lnet_status()

    if not lnet_loaded:
        raise RuntimeError("Cannot detect LNet NIDs, lnet module is not loaded")

    if not lnet_up:
        raise RuntimeError("Cannot detect LNet NIDs, lnet is not up")

    # Read active NIDs from /proc
    lines = open("/proc/sys/lnet/nis").readlines()
    # Skip header line
    lines = lines[1:]

    # Parse each NID string out into result list
    lnet_nids = []
    for line in lines:
        tokens = line.split()
        if tokens[0] != "0@lo":
            lnet_nids.append(tokens[0])

    return lnet_nids


class LnetScanPlugin(ActionPlugin):
    def register_commands(self, parser):
        p = parser.add_parser("lnet-scan",
                              help="scan for LNet details")
        p.set_defaults(func=lnet_scan)
