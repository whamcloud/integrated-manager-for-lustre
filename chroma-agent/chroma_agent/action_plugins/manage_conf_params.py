#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import simplejson as json
from chroma_agent.shell import try_run
from chroma_agent.plugins import ActionPlugin


def set_conf_param(args):
    kwargs = json.loads(args.args)
    key = kwargs['key']
    value = kwargs['value']

    if value:
        try_run(['lctl', 'conf_param', "%s=%s" % (key, value)])
    else:
        try_run(['lctl', 'conf_param', "-d", key])


class ConfParamPlugin(ActionPlugin):
    def register_commands(self, parser):
        p = parser.add_parser("set-conf-param",
                              help="set/delete a Lustre config param")
        p.add_argument("--args", required=True,
                       help="some stuff to set")
        p.set_defaults(func=set_conf_param)
