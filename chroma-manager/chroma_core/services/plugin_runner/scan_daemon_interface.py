#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from chroma_core.services.rpc import ServiceRpcInterface


class ScanDaemonRpcInterface(ServiceRpcInterface):
    methods = ['remove_resource', 'modify_resource']
