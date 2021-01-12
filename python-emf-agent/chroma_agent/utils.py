# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from collections import defaultdict
import re

from chroma_agent.lib.shell import AgentShell


def lsof(pid=None, file=None):
    lsof_args = ["lsof", "-F", "pan0"]

    if pid:
        lsof_args += ["-p", str(pid)]

    if file:
        lsof_args += [file]

    pids = defaultdict(dict)
    current_pid = None

    rc, stdout, stderr = AgentShell.run_old(lsof_args)
    if rc != 0:
        if stderr:
            raise RuntimeError(stderr)
        # lsof exits non-zero if there's nothing holding the file open
        return pids

    for line in stdout.split("\n"):
        match = re.match(r"^p(\d+)\x00", line)
        if match:
            current_pid = match.group(1)
            continue

        match = re.match(r"^a(\w)\x00n(.*)\x00", line)
        if match:
            mode = match.group(1)
            file = match.group(2)
            pids[current_pid][file] = {"mode": mode}

    return pids
