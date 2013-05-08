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
