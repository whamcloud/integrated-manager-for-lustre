# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import os

import copy

from jinja2 import Environment, PackageLoader

from chroma_agent import config
from chroma_agent.config_store import ConfigKeyExistsError
from chroma_agent.cli import raw_result
from chroma_agent.copytool_monitor import Copytool, COPYTOOL_PROGRESS_INTERVAL
from chroma_agent.log import copytool_log
from iml_common.lib.service_control import ServiceControl
from iml_common.lib.agent_rpc import agent_error, agent_result_ok


env = Environment(loader=PackageLoader('chroma_agent', 'templates'))


def _init_file_name(service_name, id):
    return os.path.join('/etc/init.d/', '%s-%s' % (service_name, id))


def _write_service_init(service_name, id, ct_path, ct_arguments):
    init_template = env.get_template(service_name)
    init_file_name = _init_file_name(service_name, id)

    with open(init_file_name, "w") as f:
        f.write(init_template.render(id=id,
                                     ct_path=ct_path,
                                     ct_arguments=ct_arguments))

    os.chmod(init_file_name, 0700)

    return init_file_name


def start_monitored_copytool(id):
    # Start the monitor first so that we have a reader on the FIFO when
    # the copytool begins emitting events. Then start the copytool

    copytool_vars = _copytool_vars(id)

    for service_name in ['chroma-copytool-monitor', 'chroma-copytool']:
        _write_service_init(service_name,
                            copytool_vars['id'],
                            copytool_vars['ct_path'],
                            copytool_vars['ct_arguments'])

        service = ServiceControl.create('%s-%s' % (service_name, id))

        service.daemon_reload()

        if service.running:
            error = service.restart()
        else:
            error = service.start()

        if error:
            return agent_error(error)

    return agent_result_ok


def stop_monitored_copytool(id):
    # Stop the monitor after the copytool so that we can relay the
    # unconfigure event.

    for service_name in ['chroma-copytool-monitor', 'chroma-copytool']:
        service = ServiceControl.create('%s-%s' % (service_name, id))

        if os.path.exists(_init_file_name(service_name, id)) and service.running:
            error = service.stop()

            if error:
                return agent_error(error)

            os.remove(_init_file_name(service_name, id))

        service.daemon_reload()         # Finally cause the system agents to see our changes.

    return agent_result_ok


def configure_copytool(id, index, bin_path, archive_number, filesystem, mountpoint, hsm_arguments):
    copytool = Copytool(id = id,
                        index = index,
                        bin_path = bin_path,
                        filesystem = filesystem,
                        mountpoint = mountpoint,
                        hsm_arguments = hsm_arguments,
                        archive_number = archive_number)

    try:
        config.set('copytools', copytool.id, copytool.as_dict())
    except ConfigKeyExistsError:
        # This can happen when we've redeployed on a worker that was
        # already configured (force-removed, etc.)
        copytool_log.warn("Copytool %s was already configured -- assuming we need to update" % copytool.id)
        update_kwargs = copytool.as_dict()
        del update_kwargs['id']
        update_copytool(copytool.id, **update_kwargs)

    return copytool.id


def unconfigure_copytool(id):
    try:
        # It's OK to do this before unconfiguring, but we should make sure
        # it always happens regardless.
        stop_monitored_copytool(id)
    except Exception as e:
        # FIXME: do this once the monitoring stuff is complete
        raise e
    config.delete('copytools', id)
    return id


def update_copytool(id, index=None, bin_path=None, archive_number=None, filesystem=None, mountpoint=None, hsm_arguments=None):
    # Need to define the kwargs for argparse -- using an inner function
    # is simpler than inspect.getargvalues() and other hackery.
    _update_copytool(id, index=index, bin_path=bin_path, archive_number=archive_number, filesystem=filesystem, mountpoint=mountpoint, hsm_arguments=hsm_arguments)


def _update_copytool(id, **kwargs):
    ct = config.get('copytools', id)
    new_ct = copy.deepcopy(ct)
    for key, val in kwargs.items():
        if val:
            new_ct[key] = val

    # Don't bother doing anything if no values changed.
    if ct == new_ct:
        return id

    # stop/unconfigure the old instance
    unconfigure_copytool(id)

    # register/start the new instance
    configure_copytool(new_ct['id'], new_ct['index'],
                      new_ct['bin_path'], new_ct['archive_number'],
                      new_ct['filesystem'], new_ct['mountpoint'],
                      new_ct['hsm_arguments'])
    start_monitored_copytool(id)

    return id


@raw_result
def list_copytools():
    """
    Return a shell-safe list of configured copytool instances.
    """
    return " ".join(config.get_section_keys('copytools'))


def _copytool_vars(id):
    settings = config.get('settings', 'agent')
    copytool = Copytool(**config.get('copytools', id))

    ct = copytool.as_dict()
    ct['event_fifo'] = copytool.event_fifo
    ct['report_interval'] = COPYTOOL_PROGRESS_INTERVAL

    return {
        'id': id,
        'ct_path': ct['bin_path'],
        'ct_arguments': settings['copytool_template'] % ct
    }


ACTIONS = [configure_copytool, update_copytool, unconfigure_copytool, start_monitored_copytool, stop_monitored_copytool, list_copytools]
CAPABILITIES = ['manage_copytools']
