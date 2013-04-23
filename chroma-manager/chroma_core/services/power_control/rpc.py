#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from chroma_core.services import log_register
from chroma_core.services.queue import ServiceQueue
from chroma_core.services.rpc import ServiceRpcInterface


log = log_register(__name__)


class PowerControlQueue(ServiceQueue):
    name = 'power_control'


class PowerControlRpc(ServiceRpcInterface):
    methods = ['register_device',
               'unregister_device',
               'reregister_device',
               'query_device_outlets',
               'toggle_device_outlets'
              ]
