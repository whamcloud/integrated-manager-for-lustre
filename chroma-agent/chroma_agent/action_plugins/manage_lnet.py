# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import os
import json

from chroma_agent.lib.shell import AgentShell
from chroma_agent.log import console_log
from chroma_agent.device_plugins.linux_network import LinuxNetworkDevicePlugin
from iml_common.lib.agent_rpc import agent_ok_or_error

IML_CONFIGURATION_FILE = '/etc/modprobe.d/iml_lnet_module_parameters.conf'
IML_CONFIGURE_FILE_JSON_HEADER = '##  '


class Module:
    def __init__(self, module_line):
        parts = module_line.split()
        self.name = parts[0]
        # "-" is the placeholder for the absence of any depending modules. i.e.:
        # video 24067 0 - Live 0xffffffffa000a000
        # vs.
        # pps_core 19130 1 ptp, Live 0xffffffffa0017000
        if parts[3] != "-":
            self.dependents = set(parts[3][:-1].split(","))
        else:
            self.dependents = set([])


def _get_loaded_mods():
    modules = {}

    for line in open("/proc/modules").readlines():
        m = Module(line.strip())
        modules[m.name] = m

    return modules


def _remove_module(name, modules):
    try:
        m = modules[name]
    except KeyError:
        # It's not loaded, do nothing.
        return None

    console_log.info("Removing %d dependents of %s : %s" % (len(m.dependents), name, m.dependents))
    while m.dependents:
        error = _remove_module(m.dependents.pop(), modules)

        if error:
            return error

    console_log.info("Removing %s" % name)

    error = AgentShell.run_canned_error_message(['rmmod', name])

    if error:
        return error

    modules.pop(name)
    for m in modules.values():
        if name in m.dependents:
            m.dependents.remove(name)

    return None


def _rmmod(module_name):
    return _remove_module(module_name, _get_loaded_mods())


def _rmmod_deps(module_name, excpt=[]):
    deps = [d for d in _get_loaded_mods()[module_name].dependents if d not in excpt]

    for module_name in deps:
        error = _rmmod(module_name)

        if error:
            return error

    return None


def start_lnet():
    '''
    Place lnet into the 'up' state.
    '''
    console_log.info("Starting LNet")

    # modprobe lust is a hack for HYD-1263 - Fix or work around LU-1279 - failure trying to mount
    # should be removed when LU-1279 is fixed
    return agent_ok_or_error(AgentShell.run_canned_error_message(["lctl", "net", "up"]) or
                             AgentShell.run_canned_error_message(["modprobe", "lustre"]))


def stop_lnet():
    '''
    Place lnet into the 'down' state, any modules that are dependent on lnet being in the 'up' state
    will be unloaded before lnet is stopped.
    '''

    console_log.info("Stopping LNet")
    return agent_ok_or_error(_rmmod_deps("lnet", excpt=["ksocklnd", "ko2iblnd"]) or
                             AgentShell.run_canned_error_message(["lctl", "net", "down"]))


def load_lnet():
    '''
    Load the lnet modules from disk into memory including an modules using the modprobe command.
    '''
    return agent_ok_or_error(AgentShell.run_canned_error_message(["modprobe", "lnet"]))


def unload_lnet():
    '''
    Unload the lnet modules from memory including an modules that are dependent on the lnet
    module.

    Lnet must be stopped before unload_lnet is called.
    '''
    return agent_ok_or_error(_rmmod('lnet'))


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
    with open(IML_CONFIGURATION_FILE, 'w') as file:
        file.write('# This file is auto-generated for Lustre NID configuration by IML\n' +
                   '# Do not overwrite this file or edit its contents directly\n')

        if (len(lnet_configuration['modprobe_entries']) > 0):
            file.write('options lnet networks=%s\n' % ','.join(lnet_configuration['modprobe_entries']))
        else:
            file.write('# No NIDs configured for Lustre\n')

        file.write('\n### LNet Configuration Data\n')

        for line in json.dumps(lnet_configuration, indent = 2).split("\n"):
            file.write('%s%s\n' % (IML_CONFIGURE_FILE_JSON_HEADER, line))

        # Our preference of course is that we read the results back from lnet, but if lnet is not up we can't
        # so we have to cache the results to use where lnet is not loaded or not up. As soon as it is up the
        # cache will be overwritten by the actual (making it I believe a cache)
        LinuxNetworkDevicePlugin.cache_results(lnet_configuration = lnet_configuration)


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
