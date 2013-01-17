#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from chroma_core.services.rpc import ServiceRpcInterface


class AgentDaemonRpcInterface(ServiceRpcInterface):
    methods = ['setup_host', 'remove_host_resources']
