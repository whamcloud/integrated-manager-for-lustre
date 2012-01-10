# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

import argparse
import json

from hydra_agent import plugins
from hydra_agent.store import AgentStore


def main():
    # FIXME: Move this into per-plugin init so that only plugins which
    # need it try to use it.
    AgentStore.setup()

    parser = argparse.ArgumentParser(description="The Whamcloud Hydra Agent")
    subparsers = parser.add_subparsers()

    for plugin in plugins.find_plugins():
        plugin.register_commands(subparsers)

    # FIXME: This really ought to be split out into a separate
    # hydra-daemon script.
    import hydra_agent.main_loop
    p = subparsers.add_parser("daemon",
                              help="start daemon (publish with Avahi)")
    p.add_argument("--foreground", action="store_true")
    p.set_defaults(func=hydra_agent.main_loop.run_main_loop)

    try:
        args = parser.parse_args()
        result = args.func(args)
        print json.dumps({'success': True, 'result': result}, indent = 2)
    except Exception, e:
        import sys
        import traceback
        import pickle

        exc_info = sys.exc_info()
        backtrace = '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))
        sys.stderr.write("%s\n" % backtrace)

        print json.dumps({'success': False,
                          'exception': pickle.dumps(e),
                          'backtrace': backtrace}, indent=2)
        # NB having caught the exception, we will finally return 0.  This
        # is done in order to distinguish between internal errors in
        # hydra-agent (nonzero return value) and exceptions while running
        # command errors (zero return value, exception serialized and output)
