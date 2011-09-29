#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

""" Library of actions that the hydra-agent can be asked to carry out."""

from hydra_agent.legacy_audit import LocalLustreAudit

from hydra_agent import shell

import errno
import os
import re
import simplejson as json

from device_scan import device_scan
from targets import *
from clear_targets import clear_targets

def locate_device(args):
    lla = LocalLustreAudit()
    lla.read_mounts()
    lla.read_fstab()
    device_nodes = lla.get_device_nodes()
    node_result = None
    for d in device_nodes:
        if d['fs_uuid'] == args.uuid:
            node_result = d
    return node_result

def fail_node(args):
    # force a manual failover by failing a node
    shell.try_run("sync; sync; init 0", shell = True)

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
            if line == "# added by hydra-agent\n":
                skip = False
                continue
        if line == "# added by hydra-agent\n":
            skip = True
            continue
        if not skip:
            os.write(tmp_f, line)
    f.close()
    if args.node != "":
        os.write(tmp_f, "# added by hydra-agent\n*.* @@%s\n" \
                        "# added by hydra-agent\n" % args.node)
    os.close(tmp_f)
    os.chmod(tmp_name, 0644)
    os.rename(tmp_name, "/etc/rsyslog.conf")

    # signal the process
    shell.try_run(['service', 'rsyslog', 'reload'])
    f.close()

def audit(args):
    return LocalLustreAudit().audit_info()

def set_conf_param(args):
    kwargs = json.loads(args.args)
    key = kwargs['key']
    value = kwargs['value']

    if value:
        shell.try_run(['lctl', 'conf_param', "%s=%s" % (key, value)])
    else:
        shell.try_run(['lctl', 'conf_param', "-d", key])

def start_lnet(args):
    shell.try_run(["lctl", "net", "up"])

def stop_lnet(args):
    from hydra_agent.rmmod import rmmod
    rmmod('ptlrpc')
    shell.try_run(["lctl", "net", "down"])

def load_lnet(args):
    shell.try_run(["modprobe", "lnet"])

def unload_lnet(args):
    from hydra_agent.rmmod import rmmod
    rmmod('lnet')
