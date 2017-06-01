# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import os

from chroma_agent.device_plugins.syslog import SYSLOG_PORT
from chroma_agent.chroma_common.lib.agent_rpc import agent_ok_or_error
from chroma_agent.chroma_common.lib.service_control import ServiceControl

rsyslog_service = ServiceControl.create('rsyslog')


def unconfigure_rsyslog():
    """
    Modify the rsyslogd configuration to stop forwarding messages to chroma

    :return: None
    """
    return _configure_rsyslog("")


def configure_rsyslog():
    """
    Modify the rsyslogd configuration to forward all messages to chroma

    :return: None
    """
    return _configure_rsyslog("127.0.0.1")


def _configure_rsyslog(destination):
    from tempfile import mkstemp
    tmp_f, tmp_name = mkstemp(dir='/etc')
    f = open('/etc/rsyslog.conf', 'r')
    skip = False
    for line in f.readlines():
        if skip:
            if line == "# added by chroma-agent\n":
                skip = False
                continue
        if line == "# added by chroma-agent\n":
            skip = True
            continue
        if not skip:
            os.write(tmp_f, line)
    f.close()
    if destination != "":
        os.write(tmp_f, "# added by chroma-agent\n" \
                        "$PreserveFQDN on\n" \
                        "*.* @@%s:%s;RSYSLOG_ForwardFormat\n" \
                        "# added by chroma-agent\n" % (destination, SYSLOG_PORT))
    os.close(tmp_f)
    os.chmod(tmp_name, 0644)
    os.rename(tmp_name, "/etc/rsyslog.conf")

    error = None

    # signal the process and restart if the signal fails.
    error = rsyslog_service.reload() and rsyslog_service.restart()

    return agent_ok_or_error(error)


ACTIONS = [configure_rsyslog, unconfigure_rsyslog]
CAPABILITIES = ['manage_rsyslog']
