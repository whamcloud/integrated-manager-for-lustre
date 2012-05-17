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
from chroma_cli.api import ApiHandle

# TODO: This kind of thing is probably a good candidate for
# pluginization, if we wind up with a lot of command modules.
from chroma_cli.commands import api_resources


def api_cli():
    config = Configuration()
    parser = ResettableArgumentParser(description="Chroma API CLI")

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


def standard_cli(args=None):
    from itertools import product
    basic_nouns = ["server", "volume", "filesystem", "ost", "mdt", "mgt", "mgs", "oss", "mds"]
    basic_verbs = ["list", "show", "add", "remove"]
    noun_verbs = ["%s-%s" % t for t in product(*[basic_nouns, basic_verbs])]
    noun_verbs.extend(["target-show", "target-list"])

    config = Configuration()
    parser = ResettableArgumentParser(description="Chroma API CLI")

    import tablib
    tablib_formats = [m.title for m in tablib.formats.available]
    parser.add_argument("--output", "-o", help="Output format",
                        choices=["human"] + tablib_formats, default="human")
    parser.clear_resets()

    parser.add_argument("primary_action", choices=basic_nouns + noun_verbs)
    parser.add_argument("options", nargs=REMAINDER)

    ns = parser.parse_args(args)

    if "-" in ns.primary_action:
        ns.noun, ns.verb = ns.primary_action.split("-")
        parser.reset()
        parser.add_argument("primary_action", choices=noun_verbs)
        if ns.verb == "show":
            parser.add_argument("subject")
        parser.add_argument("options", nargs=REMAINDER)
        ns = parser.parse_args(args, ns)
    else:
        parser.reset()
        parser.add_argument("noun", choices=basic_nouns)
        parser.add_argument("subject")
        parser.add_argument("secondary_action",
                            choices=[c for c in noun_verbs if '-list' in c])
        parser.add_argument("options", nargs=REMAINDER)
        ns = parser.parse_args(args)
        ns.secondary_noun, ns.verb = ns.secondary_action.split("-")

    def _noun2endpoint(noun):
        if noun == "server":
            return "host", {}
        if noun in ["mgt", "mdt", "ost"]:
            return "target", {'kind': noun}
        if noun in ["mgs", "mds", "oss"]:
            return "host", {'role': noun}

        return noun, {}

    api = ApiHandle()
    api.base_url = config.api_url
    api.authentication = {'username': config.username,
                          'password': config.password}

    if ns.verb in ["list", "show"]:
        entities = []
        if 'primary_action' in ns:
            ep_name, kwargs = _noun2endpoint(ns.noun)
            if ns.verb == "list":
                entities = api.endpoints[ep_name].list(**kwargs)
            elif ns.verb == "show":
                entities = [api.endpoints[ep_name].show(ns.subject)]
        else:
            if ns.noun == "filesystem":
                fs = api.endpoints['filesystem'].show(ns.subject)
                kwargs = {'filesystem_id': fs['id']}
                if '--primary' in ns.options:
                    kwargs['primary'] = True

                if ns.secondary_noun in ["ost", "mdt", "mgt"]:
                    kwargs['kind'] = ns.secondary_noun
                    entities = api.endpoints['target'].list(**kwargs)
                elif ns.secondary_noun == "target":
                    entities = api.endpoints['target'].list(**kwargs)
                elif ns.secondary_noun == "server":
                    entities = api.endpoints['host'].list(**kwargs)
                elif ns.secondary_noun in ["oss", "mds", "mgs"]:
                    kwargs['role'] = ns.secondary_noun
                    entities = api.endpoints['host'].list(**kwargs)
                elif ns.secondary_noun == "volume":
                    entities = api.endpoints['volume'].list(**kwargs)
            elif ns.noun == "server":
                host = api.endpoints['host'].show(ns.subject)
                kwargs = {'host_id': host['id']}
                if '--primary' in ns.options:
                    kwargs['primary'] = True

                if ns.secondary_noun in ["ost", "mdt", "mgt"]:
                    kwargs['kind'] = ns.secondary_noun
                    entities = api.endpoints['target'].list(**kwargs)
                elif ns.secondary_noun == "target":
                    entities = api.endpoints['target'].list(**kwargs)
                elif ns.secondary_noun == "volume":
                    entities = api.endpoints['volume'].list(**kwargs)

        if ns.output == "json":
            from tablib.packages import omnijson as json
            print json.dumps([e.all_attributes for e in entities])
        elif ns.output == "yaml":
            from tablib.packages import yaml
            print yaml.safe_dump([e.all_attributes for e in entities])
        else:
            try:
                header = entities[0].as_header()
                rows = []
                for entity in entities:
                    rows.append(entity.as_row())

                if ns.output == "human":
                    from prettytable import PrettyTable, NONE
                    table = PrettyTable(header, hrules=NONE)
                    for row in rows:
                        table.add_row(row)
                    print table
                else:
                    data = tablib.Dataset(*rows, headers=header)
                    format = getattr(data, ns.output)
                    print format
            except IndexError:
                print "Found 0 results for %s" % ns.verb
    else:
        raise RuntimeError("Sorry, '%s' is not implemented yet!" % ns.verb)

    sys.exit(0)

if __name__ == '__main__':
    standard_cli()
