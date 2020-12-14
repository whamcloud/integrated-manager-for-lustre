# -*- coding: utf-8 -*-
# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import argparse
import inspect
import sys
import traceback
import json

from chroma_agent.lib.shell import AgentShell
from chroma_agent.plugin_manager import ActionPluginManager


def configure_logging():
    import logging
    from chroma_agent.log import console_log, daemon_log

    console_log.addHandler(logging.StreamHandler(sys.stderr))
    console_log.setLevel(logging.INFO)
    daemon_log.addHandler(logging.StreamHandler(sys.stderr))
    daemon_log.setLevel(logging.WARNING)


def raw_result(wrapped):
    """
    Decorator for functions whose output should not be JSON-serialized.
    """

    def wrapper(*args, **kwargs):
        result = wrapped(*args, **kwargs)
        return {"raw_result": result}

    # These contortions are necessary to retain compatibility with
    # argparse's ability to generate CLI options by signature inspection.
    import functools

    wrapped_signature = inspect.getargspec(wrapped)
    formatted_args = inspect.formatargspec(*wrapped_signature)
    compat_name = "_%s" % wrapped.func_name
    compat_def = "lambda %s: %s%s" % (
        formatted_args.lstrip("(").rstrip(")"),
        compat_name,
        formatted_args,
    )
    compat_fn = eval(compat_def, {compat_name: wrapper})
    return functools.wraps(wrapped)(compat_fn)


def _register_function(parser, name, fn):
    """
    Generate approximate mapping of ActionPlugin functions
    to CLI commands.  In production these functions get invoked
    via AgentClient, but exposing them to the CLI is useful for
    debugging, and for the inital setup command.
    """
    argspec = inspect.getargspec(fn)

    # agent_daemon_context is used to pass daemon context to the agnet, the user cannot provide it and
    # so functions that require it cannot be called from the CLI
    # In future we might want to 'create' a context so these functions can be called, but today the only
    # usages do not make sense to call from the CLI.
    if "agent_daemon_context" in argspec[0]:
        return

    p = parser.add_parser(name, help=fn.__doc__)

    def wrap(args):
        args = vars(args)
        del args["func"]
        return fn(**args)

    p.set_defaults(func=wrap)

    if argspec.defaults is not None:
        positional_arg_count = len(argspec.args) - len(argspec.defaults)
    else:
        positional_arg_count = len(argspec.args)

    for i, arg in enumerate(argspec.args):
        if i < positional_arg_count:
            p.add_argument("--%s" % arg, required=True)
        else:
            if isinstance(argspec.defaults[i - positional_arg_count], bool):
                p.add_argument("--%s" % arg, required=False, action="store_true")
            else:
                p.add_argument("--%s" % arg, required=False)


def main():
    configure_logging()

    parser = argparse.ArgumentParser(description="Integrated Manager for Lustre software Agent")
    subparsers = parser.add_subparsers()

    for command, fn in ActionPluginManager().commands.items():
        _register_function(subparsers, command, fn)

    try:
        AgentShell.thread_state.enable_save()
        args = parser.parse_args()
        result = args.func(args)
        try:
            print(result["raw_result"])
        except (TypeError, KeyError):
            sys.stderr.write(json.dumps(AgentShell.thread_state.get_subprocesses(), indent=2))
            sys.stderr.write("\n\n")
            print(json.dumps({"success": True, "result": result}, indent=2))
    except SystemExit:
        raise
    except Exception:
        exc_info = sys.exc_info()
        backtrace = "\n".join(traceback.format_exception(*(exc_info or sys.exc_info())))
        sys.stderr.write("%s\n" % backtrace)

        sys.stderr.write(json.dumps(AgentShell.thread_state.get_subprocesses(), indent=2))
        sys.stderr.write("\n\n")
        print(json.dumps({"success": False, "backtrace": backtrace}, indent=2))
        # NB having caught the exception, we will finally return 0.  This
        # is done in order to distinguish between internal errors in
        # chroma-agent (nonzero return value) and exceptions while running
        # command errors (zero return value, exception serialized and output)
