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


def iptables(op, chain, args):
    op_arg = ""
    if op == "add":
        op_arg = "-I"
    elif op == "del":
        op_arg = "-D"
    else:
        raise RuntimeError("invalid mode: %s" % op)

    rc, stdout, stderr = shell.run(["service", "iptables", "status"])
    if rc == 0 and stdout != '''Table: filter
Chain INPUT (policy ACCEPT)
num  target     prot opt source               destination         

Chain FORWARD (policy ACCEPT)
num  target     prot opt source               destination         

Chain OUTPUT (policy ACCEPT)
num  target     prot opt source               destination         

''':
        cmdlist = ["/sbin/iptables", op_arg, chain]
        cmdlist.extend(args)
        shell.try_run(cmdlist)


def add_firewall_rule(port, proto, port_desc):
    console_log.info("Opening firewall for %s" % port_desc)
    # install a firewall rule for this port
    shell.try_run(['/usr/sbin/lokkit', '-n', '-p', '%s:%s' % (port, proto)])
    # XXX using -n above and installing the rule manually here is a
    #     dirty hack due to lokkit completely restarting the firewall
    #     interrupts existing sessions
    iptables("add", 'INPUT', ['4', '-m', 'state', '--state', 'new',
             '-p', proto, '--dport', str(port), '-j', 'ACCEPT'])


def del_firewall_rule(port, proto, port_desc):
    console_log.info("Closing firewall for %s" % port_desc)
    # it really bites that lokkit has no "delete" functionality
    iptables("del", 'INPUT', ['-m', 'state', '--state', 'new', '-p',
             proto, '--dport', str(port), '-j', 'ACCEPT'])
    import os
    from tempfile import mkstemp
    import shutil
    import errno
    try:
        tmp = mkstemp(dir = "/etc/sysconfig")
        with os.fdopen(tmp[0], "w") as tmpf:
            for line in open("/etc/sysconfig/iptables").readlines():
                if line.rstrip() != "-A INPUT -m state --state NEW -m %s -p %s --dport %s -j ACCEPT" % (proto, proto, port):
                    tmpf.write(line)
            tmpf.flush()
        shutil.move(tmp[1], "/etc/sysconfig/iptables")
    except IOError, e:
        if e.errno != errno.ENOENT:
            raise

    try:
        tmp = mkstemp(dir = "/etc/sysconfig")
        with os.fdopen(tmp[0], "w") as tmpf:
            for line in open("/etc/sysconfig/system-config-firewall").readlines():
                if line.rstrip() != "--port=%s:udp" % port:
                    tmpf.write(line)
            tmpf.flush()
        shutil.move(tmp[1], "/etc/sysconfig/system-config-firewall")
    except IOError, e:
        if e.errno != errno.ENOENT:
            raise
