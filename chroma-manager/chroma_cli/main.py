# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from argparse import REMAINDER

from chroma_cli.exceptions import BadRequest
from chroma_cli.parser import ResettableArgumentParser
from chroma_cli.config import Configuration

# TODO: This kind of thing is probably a good candidate for
# pluginization, if we wind up with a lot of command modules.
from chroma_cli.commands import api_resources


def main():
    config = Configuration()
    parser = ResettableArgumentParser(description="Chroma CLI")

    # register global arguments for each module
    api_resources.register_global_arguments(parser)

    # freeze global arguments
    parser.clear_resets()

    # first-phase positional arguments
    parser.add_argument("resource", help='command or resource ("resources list") for a list')
    parser.add_argument("verb", nargs="?", help="action to perform on specified resource, if appropriate")
    parser.add_argument("args", nargs=REMAINDER, help="arguments for resource verb")

    ns = parser.parse_args()

    # Allow CLI options to override defaults/.chroma config values
    config.update(dict([[key, val] for key, val in ns.__dict__.items()
                                if val != None
                                and key not in ["resource", "verb", "args"]]))

    command_dispatcher = {}
    # each module can register a set of static command handlers
    command_dispatcher.update(api_resources.commands())

    try:
        try:
            # First try dispatching to known, static handlers
            command_dispatcher[ns.resource](config, parser, ns)
        except KeyError:
            # If that fails, throw it at the api resources dispatcher and
            # see if it sticks.
            api_resources.dispatch(config, parser, ns)
    except BadRequest, e:
        print "Failed validation check(s):"
        print e
