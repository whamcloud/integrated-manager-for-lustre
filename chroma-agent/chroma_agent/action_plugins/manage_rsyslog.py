#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from chroma_agent.device_plugins.syslog import SYSLOG_PORT
import os
from chroma_agent import shell


def unconfigure_rsyslog():
    """
    Modify the rsyslogd configuration to stop forwarding messages to chroma

    :return: None
    """
    _configure_rsyslog("")


def configure_rsyslog():
    """
    Modify the rsyslogd configuration to forward all messages to chroma

    :return: None
    """
    _configure_rsyslog("127.0.0.1")


def _configure_rsyslog(destination):
    from tempfile import mkstemp
    tmp_f, tmp_name = mkstemp(dir = '/etc')
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

    # signal the process
    rc, stdout, stderr = shell.run(['service', 'rsyslog', 'reload'])
    if rc != 0:
        shell.try_run(['service', 'rsyslog', 'restart'])


ACTIONS = [configure_rsyslog, unconfigure_rsyslog]
CAPABILITIES = ['manage_rsyslog']
