#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2016 Intel Corporation All Rights Reserved.
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


from chroma_agent.chroma_common.lib.ntp import NTPConfig
from chroma_agent.chroma_common.lib.agent_rpc import agent_ok_or_error
from chroma_agent.chroma_common.lib.service_control import ServiceControl


ntp_service = ServiceControl.create('ntpd')


def unconfigure_ntp():
    """
    Unconfigure the ntp client

    :return: Value using simple return protocol
    """
    return configure_ntp(None)


def configure_ntp(ntp_server):
    """
    Change the ntp configuration file to use the server passed

    :return: Value using simple return protocol
    """
    error = NTPConfig().add(ntp_server)
    if error:
        return error
    else:
        return agent_ok_or_error(ntp_service.restart())


ACTIONS = [configure_ntp, unconfigure_ntp]
CAPABILITIES = ['manage_ntp']
