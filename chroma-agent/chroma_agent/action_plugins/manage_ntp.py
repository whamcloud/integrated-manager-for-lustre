#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import os

from chroma_agent import shell


def unconfigure_ntp():
    configure_ntp(ntp_server = "")


def configure_ntp(ntp_server):
    from tempfile import mkstemp
    from time import sleep
    tmp_f, tmp_name = mkstemp(dir = '/etc')
    f = open('/etc/ntp.conf', 'r')
    added_server = False
    COMMENT_PREFIX = "# Commented by chroma-agent: "
    ADD_SUFFIX = " # Added by chroma-agent"
    for line in f.readlines():
        if ntp_server:
            # Comment out existing server lines and add one of our own
            if line.startswith("server "):
                if not added_server:
                    os.write(tmp_f, "server %s%s\n" % (ntp_server, ADD_SUFFIX))
                    added_server = True
                line = "%s%s" % (COMMENT_PREFIX, line)
        else:
            # Remove anything we added, and uncomment anything we commented
            if line.startswith("server "):
                continue
            elif line.startswith(COMMENT_PREFIX):
                line = line[len(COMMENT_PREFIX):]
        os.write(tmp_f, line)

    if ntp_server and not added_server:
        # This can happen if there was no existing 'server' line for
        # us to insert before
        os.write(tmp_f, "server %s%s\n" % (ntp_server, ADD_SUFFIX))

    f.close()
    os.close(tmp_f)
    os.chmod(tmp_name, 0644)
    if not os.path.exists("/etc/ntp.conf.pre-chroma"):
        os.rename("/etc/ntp.conf", "/etc/ntp.conf.pre-chroma")
    os.rename(tmp_name, "/etc/ntp.conf")

    if ntp_server:
        # If we have a server, sync time to it now before letting ntpd take over
        shell.try_run(['service', 'ntpd', 'stop'])

        timeout = 300
        sleep_time = 5
        while timeout > 0:
            rc, stdout, stderr = shell.run(['service', 'ntpdate', 'restart'])
            if rc == 0:
                break
            else:
                sleep(sleep_time)
                timeout -= sleep_time

        # did we time out?
        if timeout < 1:
            raise RuntimeError("Timed out waiting for time sync from the Chroma Manager.  You could try waiting a few minutes and clicking \"Set up server\" for this server")

        # signal the process
        shell.try_run(['service', 'ntpd', 'start'])
    else:
        # With no server, just restart ntpd, don't worry about the sync
        shell.try_run(['service', 'ntpd', 'restart'])


ACTIONS = [configure_ntp, unconfigure_ntp]
CAPABILITIES = ['manage_ntp']
