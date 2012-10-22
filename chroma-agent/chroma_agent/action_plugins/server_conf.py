#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import datetime

from chroma_agent.plugins import ActionPlugin


def _validate_conf(server_conf):
    from chroma_agent.agent_daemon import send_update
    result = send_update(
            server_conf['url'],
            server_conf['token'],
            {'id': None, 'counter': 0},
            datetime.datetime.utcnow(),
            {})
    if result == None:
        from socket import getfqdn
        raise RuntimeError("Cannot contact server URL %s from %s" % (server_conf['url'], getfqdn()))


def _service_is_running():
    from chroma_agent.shell import run
    return run(["/sbin/service", "chroma-agent", "status"])[0] == 0


def _start_service():
    from chroma_agent.shell import try_run
    try_run(["/sbin/service", "chroma-agent", "start"])


def _service_is_enabled():
    from chroma_agent.shell import run
    return run(["/sbin/chkconfig", "chroma-agent"])[0] == 0


def _enable_service():
    from chroma_agent.shell import try_run
    try_run(["/sbin/chkconfig", "chroma-agent", "on"])


def set_server_conf(args = None):
    import simplejson as json
    server_conf = json.loads(args.args)

    _validate_conf(server_conf)

    from chroma_agent.store import AgentStore
    AgentStore.set_server_conf(server_conf)

    if not _service_is_enabled():
        from chroma_agent.log import agent_log
        agent_log.warning("chroma-agent service was disabled.  Re-enabling.")
        _enable_service()

    if not _service_is_running():
        from chroma_agent.log import agent_log
        agent_log.warning("chroma-agent service was stopped.  Re-starting.")
        _start_service()


def remove_server_conf(args = None):
    from chroma_agent.store import AgentStore
    AgentStore.remove_server_conf()


class ServerConfPlugin(ActionPlugin):
    def register_commands(self, parser):
        p = parser.add_parser("set-server-conf",
                              help="set server config params")
        p.add_argument("--args", required=True,
                       help="config params to be set")
        p.set_defaults(func=set_server_conf)

        p = parser.add_parser("remove-server-conf",
                              help="unset server config params")
        p.set_defaults(func=remove_server_conf)
