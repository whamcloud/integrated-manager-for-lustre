#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import argparse
import inspect
import logging
from chroma_agent import shell
import simplejson as json
import sys
import traceback

from chroma_agent.log import console_log, daemon_log
from chroma_agent.plugin_manager import ActionPluginManager


def _register_function(parser, name, fn):
    """
    Generate approximate mapping of ActionPlugin functions
    to CLI commands.  In production these functions get invoked
    via AgentClient, but exposing them to the CLI is useful for
    debugging, and for the inital setup command.
    """
    argspec = inspect.getargspec(fn)

    p = parser.add_parser(name, help = fn.__doc__)

    def wrap(args):
        args = vars(args)
        del args['func']
        return fn(**args)

    p.set_defaults(func = wrap)

    if argspec.defaults is not None:
        positional_arg_count = len(argspec.args) - len(argspec.defaults)
    else:
        positional_arg_count = len(argspec.args)

    for i, arg in enumerate(argspec.args):
        if i < positional_arg_count:
            p.add_argument('--%s' % arg, required = True)
        else:
            if isinstance(argspec.defaults[i - positional_arg_count], bool):
                p.add_argument('--%s' % arg, required = False, action = 'store_true')
            else:
                p.add_argument('--%s' % arg, required = False)


def main():
    console_log.addHandler(logging.StreamHandler(sys.stderr))
    console_log.setLevel(logging.INFO)
    daemon_log.addHandler(logging.StreamHandler(sys.stderr))
    daemon_log.setLevel(logging.WARNING)

    parser = argparse.ArgumentParser(description="Whamcloud Chroma Agent")
    subparsers = parser.add_subparsers()

    for command, fn in ActionPluginManager().commands.items():
        _register_function(subparsers, command, fn)

    try:
        shell.logs.enable_save()
        args = parser.parse_args()
        result = args.func(args)
        sys.stderr.write(json.dumps(shell.logs.get_subprocesses(), indent = 2))
        sys.stderr.write("\n\n")
        print json.dumps({'success': True, 'result': result}, indent = 2)
    except SystemExit:
        raise
    except Exception:
        exc_info = sys.exc_info()
        backtrace = '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))
        sys.stderr.write("%s\n" % backtrace)

        sys.stderr.write(json.dumps(shell.logs.get_subprocesses(), indent = 2))
        sys.stderr.write("\n\n")
        print json.dumps({'success': False,
                          'backtrace': backtrace}, indent=2)
        # NB having caught the exception, we will finally return 0.  This
        # is done in order to distinguish between internal errors in
        # chroma-agent (nonzero return value) and exceptions while running
        # command errors (zero return value, exception serialized and output)
