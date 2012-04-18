#!/usr/bin/python
#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import sys

from chroma_agent.log import agent_log
from chroma_agent import shell

# Extra deps not expressed in lsmod's list of dependent modules
extra_deps = {"lquota": set(["lov", "osc", "mgc", "mds", "mdc", "lmv"])}


class Module:
    def __init__(self, lsmod_line):
        parts = lsmod_line.split()
        self.name = parts[0]
        try:
            self.dependents = set(parts[3].split(","))
        except IndexError:
            self.dependents = set([])


def _load_lsmod():
    modules = {}

    stdout = shell.try_run(["/sbin/lsmod"])
    lines = [i for i in stdout.split("\n")[1:] if len(i) > 0]
    for line in lines:
        m = Module(line.strip())
        modules[m.name] = m

    for name, module in modules.items():
        try:
            module.dependents |= (extra_deps[name] & set(modules.keys()))
        except KeyError:
            pass

    return modules


def _remove_module(name, modules):
    try:
        m = modules[name]
    except KeyError:
        # It's not loaded, do nothing.
        return
    agent_log.info("Removing %d dependents of %s : %s" % (len(m.dependents), name, m.dependents))
    while (len(m.dependents) > 0):
        _remove_module(m.dependents.pop(), modules)

    agent_log.info("Removing %s" % name)
    shell.try_run(['rmmod', name])

    modules.pop(name)
    for m in modules.values():
        if name in m.dependents:
            m.dependents.remove(name)


def rmmod(module_name):
    modules = _load_lsmod()
    _remove_module(module_name, modules)

if __name__ == '__main__':
    rmmod(sys.argv[1])
