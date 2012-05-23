#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


"""Rsyslog actions."""

from chroma_agent import shell
from chroma_agent.plugins import ActionPlugin

import os


def unconfigure_rsyslog(args):
    args.node = ""
    configure_rsyslog(args)


def configure_rsyslog(args):
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
    if args.node != "":
        os.write(tmp_f, "# added by chroma-agent\n" \
                        "*.* @@%s;RSYSLOG_ForwardFormat\n" \
                        "# added by chroma-agent\n" % args.node)
    os.close(tmp_f)
    os.chmod(tmp_name, 0644)
    os.rename(tmp_name, "/etc/rsyslog.conf")

    # signal the process
    rc, stdout, stderr = shell.run(['service', 'rsyslog', 'reload'])
    if rc != 0:
        shell.try_run(['service', 'rsyslog', 'restart'])

    f.close()


class RsyslogPlugin(ActionPlugin):
    def register_commands(self, parser):
        p = parser.add_parser("configure-rsyslog",
                              help="configure rsyslog forwarding")
        p.add_argument("--node", required=True,
                       help="syslog aggregation node")
        p.set_defaults(func=configure_rsyslog)

        p = parser.add_parser("unconfigure-rsyslog",
                              help="unconfigure rsyslog forwarding")
        p.set_defaults(func=unconfigure_rsyslog)
