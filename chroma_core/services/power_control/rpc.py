# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from chroma_core.services import log_register
from chroma_core.services.rpc import ServiceRpcInterface


log = log_register(__name__)


class PowerControlRpc(ServiceRpcInterface):
    methods = [
        "register_device",
        "unregister_device",
        "reregister_device",
        "query_device_outlets",
        "toggle_device_outlets",
    ]
