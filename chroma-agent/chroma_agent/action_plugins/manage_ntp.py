#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2015 Intel Corporation All Rights Reserved.
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


import os
from tempfile import mkstemp

from chroma_agent.chroma_common.lib import shell


def unconfigure_ntp():
    configure_ntp(ntp_server = "")


def configure_ntp(ntp_server):
    added_server = False
    PRECHROMA_NTP_FILE = '/etc/ntp.conf.pre-chroma'
    NTP_FILE = '/etc/ntp.conf'
    COMMENT_PREFIX = "# Commented by chroma-agent: "
    ADD_SUFFIX = " # Added by chroma-agent"

    tmp_f, tmp_name = mkstemp(dir = '/etc')

    f = open(NTP_FILE, 'r')

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
    if not os.path.exists(PRECHROMA_NTP_FILE):
        os.rename(NTP_FILE, PRECHROMA_NTP_FILE)
    os.rename(tmp_name, NTP_FILE)

    if ntp_server:
        timeout = 6
        while timeout > 0:
            # This rather strange code is a result of HYD-3988. The segfault SEEMS to be isolated to the case where
            # 'service ntpdate restart' is run by shell._run . If as is the case here 'service ntpdate restart' runs
            # whilst shell._run is executing then the segfault does not occur.
            # This is evidenced by the fact that the code below runs 'service ntpdate restart' in 1 minute and then
            # runs another command to detect that it was run. This doesn't cause a segfault. At some point once the
            # root cause is resolved the patch should be reverted back to some reasonable code.
            tmp_f, tmp_name = mkstemp(dir = '/root')
            os.write(tmp_f, "service ntpd stop\nservice ntpdate restart\nservice ntpd start\nrm -f %s" % tmp_name)
            os.close(tmp_f)

            # So run the service commands via the file above in 1 min - then wait for the command to finish by looking
            # for the self deleting file to exit. Not the action runner process will timeout these commands should they
            # hang
            shell.try_run(['at', '-M', 'now', '+0', 'min', '-f', tmp_name])
            shell.try_run(['bash', '-c', 'while [ -f %s ]; do echo *; sleep 1; done' % tmp_name])

            rc, stdout, stderr = shell.run(['service', 'ntpdate', 'status'])

            if rc == 0:
                break
            else:
                timeout -= 1

        # did we time out?
        if timeout <= 0:
            raise RuntimeError("Timed out waiting for time sync from the Chroma Manager.  You could try waiting a few minutes and clicking \"Set up server\" for this server")
    else:
        # With no server, just restart ntpd, don't worry about the sync
        shell.try_run(['service', 'ntpd', 'restart'])


ACTIONS = [configure_ntp, unconfigure_ntp]
CAPABILITIES = ['manage_ntp']
