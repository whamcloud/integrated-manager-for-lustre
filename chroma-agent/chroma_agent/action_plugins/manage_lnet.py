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
    # hack for HYD-1263 - Fix or work around LU-1279 - failure trying to mount
    # should be removed when LU-1279 is fixed
    shell.try_run(["modprobe", "lustre"])


def unload_lnet():
    _rmmod('lnet')


ACTIONS = [start_lnet, stop_lnet, load_lnet, unload_lnet]
CAPABILITIES = ['manage_lnet']
