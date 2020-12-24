# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import json
import socket
from chroma_agent.lib.shell import AgentShell


def scanner_cmd(cmd):
    # Because we are pulling from device-scanner,
    # It is very important that we wait for
    # the udev queue to settle before requesting new data
    AgentShell.run(["udevadm", "settle"])

    client = socket.socket(socket.AF_UNIX)
    client.settimeout(10)
    client.connect_ex("/var/run/device-scanner.sock")
    client.sendall(json.dumps(cmd) + "\n")

    out = ""
    begin = 0

    while True:
        out += client.recv(1024)
        # Messages are expected to be separated by a newline
        # But sometimes it is not placed in the end of the line
        # Thus, take out only the first one
        idx = out.find("\n", begin)

        if idx >= 0:

            try:
                return json.loads(out[:idx])
            except ValueError:
                return None
        begin = len(out)


def parse_local_mounts(xs):
    """process block device info returned by device-scanner to produce
    a legacy version of local mounts
    """
    return [(d["source"], d["target"], d["fs_type"]) for d in xs]


def get_local_mounts():
    xs = scanner_cmd("GetMounts")
    return parse_local_mounts(xs)
