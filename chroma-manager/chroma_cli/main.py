#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from argparse import REMAINDER
import sys
import traceback

from chroma_cli.exceptions import BadRequest, InternalError, NotFound
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
        # Static handlers
        dispatcher = command_dispatcher[ns.resource]
    except KeyError:
        # Dynamic handlers from API introspection
        dispatcher = api_resources.dispatch

    try:
        dispatcher(config, parser, ns)
    except BadRequest, e:
        print "Validation errors:"
        print e
        sys.exit(1)
    except InternalError, e:
        print "Internal server error:"
        print e
        sys.exit(2)
    except NotFound, e:
        print "Not found:"
        print e
        sys.exit(4)
    except Exception, e:
        # Handlers are plugin-like so do some unexpected exception handling
        exc_info = sys.exc_info()
        trace = '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))
        print "Internal client error from handler '%s': %s" % (dispatcher, trace)
        sys.exit(3)

if __name__ == '__main__':
    main()
