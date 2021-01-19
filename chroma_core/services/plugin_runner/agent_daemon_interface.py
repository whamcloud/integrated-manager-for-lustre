# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from chroma_core.services.rpc import ServiceRpcInterface


class AgentDaemonRpcInterface(ServiceRpcInterface):
    methods = ["setup_host", "update_host_resources", "remove_host_resources", "rebalance_host_volumes"]
