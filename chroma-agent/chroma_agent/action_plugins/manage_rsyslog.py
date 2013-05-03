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
