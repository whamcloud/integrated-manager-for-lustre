#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2014 Intel Corporation All Rights Reserved.
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
import simplejson as json
import os


# Extra deps not expressed in lsmod's list of dependent modules
RMMOD_EXTRA_DEPS = {"lquota": set(["lov", "osc", "mgc", "mds", "mdc", "lmv"])}

IML_CONFIGURATION_FILE = '/etc/modprobe.d/iml_lnet_module_parameters.conf'


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
    console_log.info("Starting LNet")
    shell.try_run(["lctl", "net", "up"])
    # hack for HYD-1263 - Fix or work around LU-1279 - failure trying to mount
    # should be removed when LU-1279 is fixed
    shell.try_run(["modprobe", "lustre"])


def stop_lnet():
    console_log.info("Stopping LNet")
    _rmmod('lvfs')
    shell.try_run(["lctl", "net", "down"])


def load_lnet():
    shell.try_run(["modprobe", "lnet"])


def unload_lnet():
    _rmmod('lnet')


def configure_lnet(lnet_configuration):
    '''
    :param lnet_configuration: Contains a list of modprobe entries for the modules.conf file
    The entries are a single array in an element name 'modprobe_entries' these elements are
    then writen out to a file before lnet is restarted. The level of restart required is dependent
    on the current state of lnet, up,down or unloaded. The state of lnet before and after should
    be the same.

    A second array call nid_tuples should also provided, this is of use to the simulator and not used
    by this routine.

    :return: None
    '''
    modprobe_fname = IML_CONFIGURATION_FILE

    with open(modprobe_fname, 'w') as file:
        file.write('# This file is auto-generated for Lustre NID configuration by IML\n' +
                   '# Do not overwrite this file or edit its contents directly\n')

        if (len(lnet_configuration['modprobe_entries']) > 0):
            file.write('options lnet networks=%s\n' % ','.join(lnet_configuration['modprobe_entries']))
        else:
            file.write('# No NIDs configured for Lustre\n')

        file.write('\n### LNet Configuration Data\n')

        for line in json.dumps(lnet_configuration, indent = 2).split("\n"):
            file.write('### %s\n' % line)


def unconfigure_lnet():
    '''
    No parameters just remove the IML configuration file.
    '''
    try:
        os.remove(IML_CONFIGURATION_FILE)
    except OSError as e:
        if e.errno is not 2:        # 2 is no such file
            raise e


ACTIONS = [start_lnet, stop_lnet, load_lnet, unload_lnet, configure_lnet, unconfigure_lnet]
CAPABILITIES = ['manage_lnet']
