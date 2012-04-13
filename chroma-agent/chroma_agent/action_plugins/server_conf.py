# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

import datetime

from chroma_agent.plugins import ActionPlugin


def _validate_conf(server_conf):
    from chroma_agent.main_loop import send_update
    result = send_update(
            server_conf['url'],
            server_conf['token'],
            {'id': None, 'counter': 0},
            datetime.datetime.utcnow(),
            {})
    if result == None:
        from socket import getfqdn
        raise RuntimeError("Cannot contact server URL %s from %s" % (server_conf['url'], getfqdn()))


def set_server_conf(args = None):
    import simplejson as json
    server_conf = json.loads(args.args)

    _validate_conf(server_conf)

    from chroma_agent.store import AgentStore
    AgentStore.set_server_conf(server_conf)


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
