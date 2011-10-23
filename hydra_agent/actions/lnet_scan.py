

import os

def lnet_scan(self):
    """Parse /proc for running LNet NIDs, and return a 2-tuple of 
       (whether lnet is up, list of NID strings)"""
    lnet_nids = []

    lnet_loaded = False
    for module_line in open("/proc/modules").readlines():
        if module_line.startswith("lnet "):
            lnet_loaded = True
            break

    if not lnet_loaded:
        raise RuntimeError("Cannot detect LNet NIDs, lnet module is not loaded")

    lnet_up = os.path.exists("/proc/sys/lnet/stats")
    if not lnet_loaded:
        raise RuntimeError("Cannot detect LNet NIDs, lnet module is not loaded")

    lines = open("/proc/sys/lnet/nis").readlines()
    # Skip header line
    for line in lines[1:]:
        tokens = line.split()
        if tokens[0] != "0@lo":
            lnet_nids.append(tokens[0])

    return lnet_nids

