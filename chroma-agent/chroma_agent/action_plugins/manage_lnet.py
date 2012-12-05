#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from chroma_agent import shell
from chroma_agent.log import console_log


# Extra deps not expressed in lsmod's list of dependent modules
RMMOD_EXTRA_DEPS = {"lquota": set(["lov", "osc", "mgc", "mds", "mdc", "lmv"])}


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
            module.dependents |= (RMMOD_EXTRA_DEPS[name] & set(modules.keys()))
        except KeyError:
            pass

    return modules


def _remove_module(name, modules):
    try:
        m = modules[name]
    except KeyError:
        # It's not loaded, do nothing.
        return
    console_log.info("Removing %d dependents of %s : %s" % (len(m.dependents), name, m.dependents))
    while m.dependents:
        _remove_module(m.dependents.pop(), modules)

    console_log.info("Removing %s" % name)
    shell.try_run(['rmmod', name])

    modules.pop(name)
    for m in modules.values():
        if name in m.dependents:
            m.dependents.remove(name)


def _rmmod(module_name):
    modules = _load_lsmod()
    _remove_module(module_name, modules)


def start_lnet():
    shell.try_run(["lctl", "net", "up"])


def stop_lnet():
    _rmmod('ptlrpc')
    shell.try_run(["lctl", "net", "down"])


def load_lnet():
    shell.try_run(["modprobe", "lnet"])

def unload_lnet():
    _rmmod('lnet')


ACTIONS = [start_lnet, stop_lnet, load_lnet, unload_lnet]
CAPABILITIES = ['manage_lnet']
