#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import argparse
import simplejson as json
from chroma_agent.agent_daemon import daemon_log_setup

from chroma_agent.plugins import ActionPluginManager


def main():
    daemon_log_setup()

    parser = argparse.ArgumentParser(description="Whamcloud Chroma Agent")
    subparsers = parser.add_subparsers()

    for plugin_name, plugin_class in ActionPluginManager.get_plugins().items():
        plugin_class().register_commands(subparsers)

    try:
        args = parser.parse_args()
        result = args.func(args)
        print json.dumps({'success': True, 'result': result}, indent = 2)
    except SystemExit:
        raise
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
        # chroma-agent (nonzero return value) and exceptions while running
        # command errors (zero return value, exception serialized and output)
