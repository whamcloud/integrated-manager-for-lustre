# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


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
        return PowerControlDevice.objects.get(pk=device_id)

    @classmethod
    def remove_device(cls, sockaddr):
        return PowerControlRpc().remove_device(sockaddr)
