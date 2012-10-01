#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from chroma_core.services.queue import ServiceQueue
from chroma_core.services.rpc import ServiceRpcInterface


class AgentDaemonQueue(ServiceQueue):
    name = 'agent'


class AgentDaemonRpcInterface(ServiceRpcInterface):
    methods = ['await_session', 'remove_host_resources']
