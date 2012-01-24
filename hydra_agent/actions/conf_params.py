# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

import simplejson as json
from hydra_agent.shell import try_run
from hydra_agent.plugins import AgentPlugin


def set_conf_param(args):
    kwargs = json.loads(args.args)
    key = kwargs['key']
    value = kwargs['value']

    if value:
        try_run(['lctl', 'conf_param', "%s=%s" % (key, value)])
    else:
        # FIXME: shouldn't this be in remove_conf_param() ?
        try_run(['lctl', 'conf_param', "-d", key])


class ConfParamPlugin(AgentPlugin):
    def register_commands(self, parser):
        p = parser.add_parser("set-conf-param",
                              help="set/delete a Lustre config param")
        p.add_argument("--args", required=True,
                       help="some stuff to set")
        p.set_defaults(func=set_conf_param)
