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


from chroma_core.services import log_register
from chroma_core.services.power_control.rpc import PowerControlRpc


log = log_register(__name__)


class PowerControlClient(object):
    @classmethod
    def query_device_outlets(cls, device):
        return PowerControlRpc().query_device_outlets(device.id)

    @classmethod
    def toggle_device_outlets(cls, toggle_state, outlets):
        outlet_ids = [o.id for o in outlets]
        return PowerControlRpc().toggle_device_outlets(toggle_state, outlet_ids)

    @classmethod
    def create_device(cls, device_data):
        from chroma_core.models import PowerControlDevice
        device_id = PowerControlRpc().create_device(device_data)
        return PowerControlDevice.objects.get(pk = device_id)

    @classmethod
    def remove_device(cls, sockaddr):
        return PowerControlRpc().remove_device(sockaddr)
