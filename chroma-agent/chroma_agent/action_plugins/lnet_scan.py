#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from chroma_agent.log import daemon_log

import os


def lnet_status():
    lnet_loaded = False
    for module_line in open("/proc/modules").readlines():
        if module_line.startswith("lnet "):
            lnet_loaded = True
            break

    lnet_up = os.path.exists("/proc/sys/lnet/stats")

    return lnet_loaded, lnet_up


def get_nids():
    # Read active NIDs from /proc
    try:
        lines = open("/proc/sys/lnet/nis").readlines()
    except IOError:
        daemon_log.warning("get_nids: failed to open")
        return None

    # Skip header line
    lines = lines[1:]

    # Parse each NID string out into result list
    lnet_nids = []
    for line in lines:
        tokens = line.split()
        if tokens[0] != "0@lo":
            lnet_nids.append(tokens[0])

    return lnet_nids


def lnet_scan():
    """Parse /proc for running LNet NIDs, and return list of NID strings"""
    lnet_loaded, lnet_up = lnet_status()

    if not lnet_loaded:
        raise RuntimeError("Cannot detect LNet NIDs, lnet module is not loaded")

    if not lnet_up:
        raise RuntimeError("Cannot detect LNet NIDs, lnet is not up")

    nids = get_nids()
    if nids is None:
        # Can happen if lnet goes down between lnet_status and here
        raise RuntimeError("Failed to detect LNet NIDs")
    return nids

ACTIONS = [lnet_scan]
CAPABILITIES = []
