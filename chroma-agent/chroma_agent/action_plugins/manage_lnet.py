#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from chroma_agent.shell import try_run
from chroma_agent.plugins import ActionPlugin


def start_lnet(args):
    try_run(["lctl", "net", "up"])


def stop_lnet(args):
    from chroma_agent.rmmod import rmmod
    rmmod('ptlrpc')
    try_run(["lctl", "net", "down"])


def load_lnet(args):
    try_run(["modprobe", "lnet"])
    # hack for HYD-1263 - Fix or work around LU-1279 - failure trying to mount two targets at the same time after boot
    # should be removed when LU-1279 is fixed
    try_run(["modprobe", "lustre"])


def unload_lnet(args):
    from chroma_agent.rmmod import rmmod
    rmmod('lnet')


class LnetPlugin(ActionPlugin):
    def register_commands(self, parser):
        p = parser.add_parser("stop-lnet",
                              help="stop LNet (lctl net down)")
        p.set_defaults(func=stop_lnet)

        p = parser.add_parser("start-lnet",
                              help="start LNet (lctl net up)")
        p.set_defaults(func=start_lnet)

        p = parser.add_parser("load-lnet",
                              help="load LNet (modprobe lnet)")
        p.set_defaults(func=load_lnet)

        p = parser.add_parser("unload-lnet",
                              help="unload LNet (rmmod lnet)")
        p.set_defaults(func=unload_lnet)
