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


import time
import copy

from chroma_agent import config
from chroma_agent.config_store import ConfigKeyExistsError
from chroma_agent.cli import raw_result
from chroma_agent import shell
from chroma_agent.shell import CommandExecutionError
from chroma_agent.copytool_monitor import Copytool, COPYTOOL_PROGRESS_INTERVAL
from chroma_agent.log import copytool_log


def start_monitored_copytool(id):
    # Start the monitor first so that we have a reader on the FIFO when
    # the copytool begins emitting events.
    try:
        shell.try_run(['/sbin/start', 'copytool-monitor', 'id=%s' % id])
    except CommandExecutionError as e:
        if 'is already running' in str(e):
            copytool_log.warn("Copytool monitor %s was already running -- restarting" % id)
            shell.try_run(['/sbin/restart', 'copytool-monitor', 'id=%s' % id])
    time.sleep(1)
    shell.try_run(['/sbin/status', 'copytool-monitor', 'id=%s' % id])

    # Next, try to start the copytool, then sleep for a second before checking
    # its status. This will catch some of the more obvious problems which
    # result in the process (re-)spawn failing right away.
    try:
        shell.try_run(['/sbin/start', 'copytool'] +
                      ["%s=%s" % item for item in _copytool_vars(id).items()])
    except CommandExecutionError as e:
        if 'is already running' in str(e):
            copytool_log.warn("Copytool %s was already running -- restarting" % id)
            shell.try_run(['/sbin/restart', 'copytool'] +
                          ["%s=%s" % item for item in _copytool_vars(id).items()])
    time.sleep(1)
    shell.try_run(['/sbin/status', 'copytool', 'id=%s' % id])


def stop_monitored_copytool(id):
    # Stop the monitor after the copytool so that we can relay the
    # unconfigure event.
    try:
        shell.try_run(['/sbin/stop', 'copytool', 'id=%s' % id])
    except CommandExecutionError as e:
        if 'Unknown instance' not in str(e):
            raise e
    try:
        shell.try_run(['/sbin/stop', 'copytool-monitor', 'id=%s' % id])
    except CommandExecutionError as e:
        if 'Unknown instance' not in str(e):
            raise e


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


@raw_result
def copytool_vars(id):
    """
    Return a shell-quoted string suitable for use within the
    start-copytools upstart task.
    """
    return " ".join(['%s="%s"' % items for items in _copytool_vars(id).items()])


ACTIONS = [configure_copytool, update_copytool, unconfigure_copytool, start_monitored_copytool, stop_monitored_copytool, list_copytools, copytool_vars]
CAPABILITIES = ['manage_copytools']
