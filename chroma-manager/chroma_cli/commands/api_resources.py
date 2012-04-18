#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import tablib

from chroma_cli.api_client import ApiClient, ApiCommandResource


def register_global_arguments(parser):
    parser.add_argument("--api-url", help="Entry URL for Chroma API")
    parser.add_argument("--username", help="Chroma username")
    parser.add_argument("--password", help="Chroma password")
    parser.add_argument("--async", help="Run asynchronously (don't wait for tasks to finish)",
                        action='store_true')


def commands():
    cmd_handlers = {
        'resources': list_resources,
        'detect_filesystems': detect_filesystems
        }

    return cmd_handlers


def list_resources(config, parser, namespace):
    api = ApiClient(config.api_url, config.username, config.password)
    print " ".join(sorted(api.resource_names))


def detect_filesystems(config, parser, args):
    api = ApiClient(config.api_url, config.username, config.password)
    endpoint = api.command
    resources = endpoint.create(message = "Detecting filesystems", jobs = [{'class_name': 'DetectTargetsJob', 'args': {}}])

    # FIXME: blob2objects turns the returned dict into a list of one ApiResource containing the dict, which
    # is not what is wanted in this case.
    command = resources[0]._data

    command = ApiCommandResource(endpoint.name, endpoint.api, **command)
    if not args.async:
        command.get_monitor()()


def add_verb_arguments(parser, verb, endpoint):
    def _str2type(string):
        try:
            return {'integer': int,
                    'boolean': bool}[string]
        except KeyError:
            # cheap default
            return str

    excluded_fields = ["available_transitions", "content_type_id",
                       "immutable_state", "last_contact", "resource_uri"]

    if verb == "create":
        excluded_fields.append("id")

    mandatory_fields = []
    if verb in ["delete", "show", "update"]:
        mandatory_fields.append("id")

    try:
        filter_fields = endpoint.filtering
    except KeyError:
        filter_fields = {}

    # TODO: Ordering? (HYD-729)

    # Build a set of arguments for this verb.
    for name, attrs in endpoint.fields.items():
        # Skip fields that should never be arguments.
        if name in excluded_fields:
            continue

        # Skip readonly fields unless this is a list request, because
        # they might be used to filter the list results.
        if attrs['readonly'] and verb != "list":
            continue

        # On list requests, skip any fields not used for filtering.
        if verb == "list" and name not in filter_fields:
            continue

        # For some verbs, it doesn't make sense to make arguments
        # out of any other fields than the minimum required.
        if (verb in ["delete", "show"] and
                name not in mandatory_fields):
            continue

        prefix = "--"
        if name in mandatory_fields:
            prefix = ""

        arg_kwargs = {'help': attrs['help_text']}
        if attrs['type'] in ["related", "list"]:
            arg_kwargs['action'] = "append"
            arg_kwargs['type'] = _str2type(attrs['type'])
        elif attrs['type'] == "boolean":
            arg_kwargs['action'] = "store_true"
            # Is this always correct?  If we don't use a
            # default of None, then the argument value is set to False
            # and included in filters, which is usually (always?) not
            # desired by default.
            # This seems interesting:
            # http://stackoverflow.com/a/9236426/204920
            arg_kwargs['default'] = None
        else:
            arg_kwargs['type'] = _str2type(attrs['type'])

        parser.add_argument("%s%s" % (prefix, name), **arg_kwargs)


def clean_args(namespace):
    excluded_keys = ["api_url", "args", "resource", "verb"]
    cleaned_args = {}
    for key, val in namespace.__dict__.items():
        if key in excluded_keys:
            continue
        if val == None:
            continue
        cleaned_args[key] = val
    return cleaned_args


def dispatch(config, parser, namespace):
    api = ApiClient(config.api_url, config.username, config.password)

    # Parse the resource being acted upon.
    parser.reset()
    parser.add_argument("resource", choices=api.resource_names)
    parser.add_argument("verb", nargs="?")  # just to make help clearer
    parser.parse_args([namespace.resource, namespace.verb], namespace)

    parser.reset()
    parser.add_argument("resource", choices=[namespace.resource])
    subparsers = parser.add_subparsers(dest="verb", description="verb")

    endpoint = api.get_endpoint(namespace.resource)

    if (namespace.verb not in endpoint.verbs + [None]
            and len(namespace.args) == 1):
        import re

        # Create a map for transition verb -> transition state
        setattr(namespace, 'states', {})

        # We might be dealing with a non-CRUD verb (e.g. a transition
        # like "stop", or "remove".  This is a little awkward, but we'll
        # make it work like other verbs, mostly.
        #
        # TODO: It would be cleaner if there were a way to query for
        # all possible transitions available to a given resource, rather
        # than querying an instance of a resource for its available
        # transitions.  Pretty sure this is a nontrivial enhancement
        # on the server side, though. (HYD-728)
        try:
            resource = endpoint.show(id=namespace.args[0])
            for t in resource.available_transitions:
                state, verb = (t['state'],
                               str(re.sub(r'\s+', '_', t['verb'].lower())))
                p = subparsers.add_parser(verb)
                p.add_argument("id", type=int)
                namespace.states[verb] = state
        except AttributeError:
            pass

    # Set up sub-parsers for each available verb and then do the
    # final argument-parsing phase.
    for verb in endpoint.verbs:
        p = subparsers.add_parser(verb)
        add_verb_arguments(p, verb, endpoint)

    ns = parser.parse_args([namespace.resource, namespace.verb]
                           + namespace.args, namespace)

    # FIXME: It's possible that we could have a conflict between the
    # endpoint's CRUD verbs and a state transition's verb.  Detecting
    # this situation in a reasonable manner is gated on a solution for
    # querying an endpoint's list of all possible transition verbs (HYD-728).
    try:
        # Normal CRUD verbs
        verb_method = getattr(endpoint, ns.verb)
        resources = verb_method(**clean_args(ns))
        if hasattr(resources, 'resource_uri'):
            # show() returns a single object
            resources = [resources]
    except KeyError:
        # Maybe a state transition?
        resources = endpoint.update(id=ns.id, state=ns.states[ns.verb],
                                    dry_run=False)

    # peel off the commands
    commands = [resources.pop(resources.index(res)) for res
                in resources if isinstance(res, ApiCommandResource)]

    if len(commands) > 1:
        raise RuntimeError("FIXME: can't deal with more than one command")

    if not ns.async:
        # lazy way to handle this
        for cmd in commands:
            monitor = cmd.get_monitor()
            monitor()

    # TODO: This is really a nasty hack.  The output should be
    # configurable, both in terms of format and maybe columns displayed?
    # At any rate, this doesn't do any kind of pagination and the
    # justification is all wonky.  It's a start, I guess. (HYD-726)
    try:
        headers = resources[0].printable_keys()
        # always make id the first column
        headers.remove("id")
        headers.insert(0, "id")
        rows = []
        for res in resources:
            row = []
            for key, val in res.printable_items():
                if key == "id":
                    row.insert(0, val)
                else:
                    # FIXME: this is nasty (HYD-727)
                    if (isinstance(val, list) or
                            isinstance(val, dict)):
                        row.append("<list>")
                    else:
                        row.append(val)
            rows.append(row)
        data = tablib.Dataset(*rows, headers=headers)
        print data.tsv
    except IndexError:
        pass
