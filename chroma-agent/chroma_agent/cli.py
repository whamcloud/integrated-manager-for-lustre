#
# INTEL CONFIDENTIAL
#
# Copyright 2013 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


import argparse
import inspect
import logging
from chroma_agent import shell
import simplejson as json
import sys
import traceback

from chroma_agent.log import console_log, daemon_log
from chroma_agent.plugin_manager import ActionPluginManager


def raw_result(wrapped):
    """
    Decorator for functions whose output should not be JSON-serialized.
    """
    def wrapper(*args, **kwargs):
        result = wrapped(*args, **kwargs)
        return {'raw_result': result}

    # These contortions are necessary to retain compatibility with
    # argparse's ability to generate CLI options by signature inspection.
    import functools
    wrapped_signature = inspect.getargspec(wrapped)
    formatted_args = inspect.formatargspec(*wrapped_signature)
    compat_name = "_%s" % wrapped.func_name
    compat_def = 'lambda %s: %s%s' % (formatted_args.lstrip('(').rstrip(')'),
                                      compat_name, formatted_args)
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

    parser = argparse.ArgumentParser(description="Intel Manager for Lustre Agent")
    subparsers = parser.add_subparsers()

    for command, fn in ActionPluginManager().commands.items():
        _register_function(subparsers, command, fn)

    try:
        shell.thread_state.enable_save()
        args = parser.parse_args()
        result = args.func(args)
        try:
            print result['raw_result']
        except (TypeError, KeyError):
            sys.stderr.write(json.dumps(shell.thread_state.get_subprocesses(), indent = 2))
            sys.stderr.write("\n\n")
            print json.dumps({'success': True, 'result': result}, indent = 2)
    except SystemExit:
        raise
    except Exception:
        exc_info = sys.exc_info()
        backtrace = '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))
        sys.stderr.write("%s\n" % backtrace)

        sys.stderr.write(json.dumps(shell.thread_state.get_subprocesses(), indent = 2))
        sys.stderr.write("\n\n")
        print json.dumps({'success': False,
                          'backtrace': backtrace}, indent=2)
        # NB having caught the exception, we will finally return 0.  This
        # is done in order to distinguish between internal errors in
        # chroma-agent (nonzero return value) and exceptions while running
        # command errors (zero return value, exception serialized and output)
