#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from itertools import product
from argparse import REMAINDER, SUPPRESS

from chroma_cli.output import StandardFormatter
from chroma_cli.exceptions import InvalidVolumeNode, TooManyMatches, BadUserInput, NotFound


class Dispatcher(object):
    def __init__(self):
        self._build_handler_map()

    def _build_handler_map(self):
        self.handlers = {}
        # NB: This only handles a single level of subclasses.
        for cls in Handler.__subclasses__():
            name = cls.nouns[0]
            if name in self.handlers:
                raise RuntimeError("Handler collision: %s:%s -> %s:%s" %
                                   (cls, name, self.handlers[name], name))
            else:
                self.handlers[name] = {}
                self.handlers[name]['klass'] = cls
                self.handlers[name]['aliases'] = cls.nouns[1:]
                self.handlers[name]['verbs'] = cls.verbs

    def _parse_noun_verb(self, ns):
        try:
            # Handle "noun-verb" format
            noun, verb = ns.args[0].split("-")
            del ns.args[0]
            return noun, verb
        except ValueError:
            pass
        except IndexError:
            return None, None

        noun = ns.args.pop(0)
        handler_name = noun
        if noun not in self.handlers:
            for name, handler in self.handlers.items():
                if noun in handler['aliases']:
                    handler_name = name
                    break
            if handler_name == noun:
                return noun, None

        try:
            if ns.args[0] in self.handlers[handler_name]['verbs']:
                # Handle "noun verb" format
                return noun, ns.args.pop(0)
            elif ns.args[0] in ["-h", "--help"]:
                # Don't mistake help for a verb
                return noun, None
        except IndexError:
            return noun, None

        # Handle "noun subject foo" format
        return noun, "context"

    def add_subparsers(self, subparsers, ns):
        # Do a bit of fiddling with the namespace created in the
        # first pass of arg parsing.
        noun, verb = self._parse_noun_verb(ns)
        if noun:
            ns.noun = noun
        if verb:
            ns.verb = verb

        # The nesting in here...  Wugh.
        for key in sorted(self.handlers.keys()):
            handler = self.handlers[key]
            noun_parser = subparsers.add_parser(key, aliases=handler['aliases'], help=", ".join(handler['verbs']))
            noun_parser.set_defaults(handler=handler['klass'])

            verb_subparsers = noun_parser.add_subparsers()
            intransitive = handler['klass'].intransitive_verbs
            irregular = handler['klass'].irregular_verbs

            for verb in handler['verbs']:
                if verb not in intransitive + irregular:
                    verb_parser = verb_subparsers.add_parser(verb, help="%s a %s" % (verb, key))
                    verb_parser.add_argument("subject", metavar=key)
                    if 'verb' in ns and ns.verb == "add":
                        # Special-case for "add"... It wants to do its
                        # own parsing in the handler.
                        verb_parser.add_argument("args", nargs=REMAINDER)
                elif verb in intransitive:
                    verb_parser = verb_subparsers.add_parser(verb, help="%s all %ss" % (verb, key))
                else:
                    # This should be fine until it's not.
                    verb_parser = verb_subparsers.add_parser(verb, help="%s for %s" % (verb, key))
                    verb_parser.add_argument("subject", metavar=key)

                verb_parser.set_defaults(handler=handler['klass'])

            if len(handler['klass'].contextual_actions()) > 0:
                ctx_parser = verb_subparsers.add_parser("context", help="%s_name action (e.g. ost-list, vol-list, etc.)" % key)
                ctx_parser.add_argument("subject", metavar=key)
                ctx_subparsers = ctx_parser.add_subparsers()
                for action in handler['klass'].contextual_actions():
                    ctx_act_parser = ctx_subparsers.add_parser(action, help="run %s in the %s context" % (action, key))
                    ctx_act_parser.add_argument("--primary", action="store_true", help="Restrict list to primaries only")
                    ctx_act_parser.set_defaults(handler=handler['klass'], contextual_action=action)


class Handler(object):
    nouns = []
    contextual_nouns = []
    verbs = ["show", "list", "add", "remove"]
    intransitive_verbs = ["list"]
    irregular_verbs = []

    @classmethod
    def contextual_actions(cls):
        # Really, the only verb that makes sense in general context is list
        return ["%s-%s" % t for t in product(*[cls.contextual_nouns, ["list"]])]

    def __init__(self, api, formatter=None):
        self.api = api

        self.output = formatter
        if not self.output:
            self.output = StandardFormatter()

        self.errors = []

    def __call__(self, parser, ns, args=None):
        try:
            ns.contextual_noun, ns.verb = ns.contextual_action.split("-")
        except AttributeError:
            pass

        if 'verb' in ns and ns.verb == "add":
            parser.reset()
            self._api_fields_to_parser_args(parser, add_help=True)
            ns = parser.parse_args(ns.args, ns)

        verb_method = getattr(self, ns.verb)
        verb_method(ns)

    def _api_fields_to_parser_args(self, parser, add_help=False):
        if add_help:
            parser.add_argument("--help", "-h",
                                help="show this help message and exit",
                                default=SUPPRESS, action='help')
        for name, attrs in self.api_endpoint.fields.items():
            if attrs['readonly']:
                continue

            kwargs = {'help': attrs['help_text']}
            if attrs['type'] in ["related", "list"]:
                kwargs['action'] = "append"
                kwargs['type'] = str
            elif attrs['type'] == "boolean":
                kwargs['action'] = "store_true"
                kwargs['default'] = False
            elif attrs['type'] == "integer":
                kwargs['type'] = int

            parser.add_argument("--%s" % name, **kwargs)

    def _resolve_volume_node(self, spec):
        try:
            hostname, path = spec.split(":")
            host = self.api.endpoints['host'].show(hostname)
            kwargs = {'host': host['id'], 'path': path}
            vn_set = self.api.endpoints['volume_node'].list(**kwargs)
            if len(vn_set) > 1:
                raise TooManyMatches()
            else:
                return vn_set[0]
        except (ValueError, IndexError):
            raise InvalidVolumeNode(spec)

    def _resolve_volume_nodes(self, specs):
        vn_list = []
        for spec in specs.split(","):
            vn_list.append(self._resolve_volume_node(spec))
        return vn_list

    def list(self, ns):
        self.output(self.api_endpoint.list())

    def show(self, ns):
        self.output(self.api_endpoint.show(ns.subject))

    def remove(self, ns):
        self.output(self.api_endpoint.delete(ns.subject))


class ServerHandler(Handler):
    nouns = ["server", "srv", "mgs", "mds", "oss"]
    contextual_nouns = ["target", "tgt", "mgt", "mdt", "ost", "volume", "vol"]
    lnet_actions = ["lnet-stop", "lnet-start", "lnet-load", "lnet-unload"]

    @classmethod
    def contextual_actions(cls):
        return cls.lnet_actions + super(ServerHandler, cls).contextual_actions()

    def __init__(self, *args, **kwargs):
        super(ServerHandler, self).__init__(*args, **kwargs)
        self.api_endpoint = self.api.endpoints['host']
        for action in self.lnet_actions:
            # NB: This will break if we ever want to add more secondary
            # actions with the same verbs to this handler.
            verb = action.split("-")[1]
            self.__dict__[verb] = self.set_lnet_state

    def set_lnet_state(self, ns):
        lnet_state = {'stop': "lnet_down",
                      'start': "lnet_up",
                      'unload': "lnet_unloaded",
                      'load': "lnet_down"}
        kwargs = {'state': lnet_state[ns.verb]}
        self.output(self.api_endpoint.update(ns.subject, **kwargs))

    def list(self, ns):
        try:
            host = self.api_endpoint.show(ns.subject)
            kwargs = {'host_id': host['id']}
            if 'primary' in ns and ns.primary:
                kwargs['primary'] = True

            if ns.contextual_noun in ["ost", "mdt", "mgt"]:
                kwargs['kind'] = ns.contextual_noun
                self.output(self.api.endpoints['target'].list(**kwargs))
            elif ns.contextual_noun in ["target", "tgt"]:
                self.output(self.api.endpoints['target'].list(**kwargs))
            elif ns.contextual_noun in ["volume", "vol"]:
                self.output(self.api.endpoints['volume'].list(**kwargs))
        except AttributeError:
            kwargs = {}
            if ns.noun in ["mgs", "mds", "oss"]:
                kwargs['role'] = ns.noun
            self.output(self.api_endpoint.list(**kwargs))

    def add(self, ns):
        kwargs = {'address': ns.subject}
        self.output(self.api_endpoint.create(**kwargs))


class FilesystemHandler(Handler):
    nouns = ["filesystem", "fs"]
    contextual_nouns = ["target", "tgt", "mgt", "mdt", "ost", "volume", "vol", "server", "mgs", "mds", "oss"]
    verbs = ["list", "show", "add", "remove", "start", "stop", "detect", "mountspec"]
    intransitive_verbs = ["list", "detect"]
    irregular_verbs = ["mountspec"]

    def __init__(self, *args, **kwargs):
        super(FilesystemHandler, self).__init__(*args, **kwargs)
        self.api_endpoint = self.api.endpoints['filesystem']

    def stop(self, ns):
        kwargs = {'state': "stopped"}
        self.output(self.api_endpoint.update(ns.subject, **kwargs))

    def start(self, ns):
        kwargs = {'state': "available"}
        self.output(self.api_endpoint.update(ns.subject, **kwargs))

    def detect(self, ns):
        kwargs = {'message': "Detecting filesystems",
                  'jobs': [{'class_name': 'DetectTargetsJob', 'args': {}}]}
        self.output(self.api.endpoints['command'].create(**kwargs))

    def list(self, ns):
        try:
            fs = self.api_endpoint.show(ns.subject)
            kwargs = {'filesystem_id': fs['id']}

            if ns.contextual_noun in ["ost", "mdt", "mgt"]:
                kwargs['kind'] = ns.contextual_noun
                self.output(self.api.endpoints['target'].list(**kwargs))
            elif ns.contextual_noun == "target":
                self.output(self.api.endpoints['target'].list(**kwargs))
            elif ns.contextual_noun == "server":
                self.output(self.api.endpoints['host'].list(**kwargs))
            elif ns.contextual_noun in ["oss", "mds", "mgs"]:
                kwargs['role'] = ns.contextual_noun
                self.output(self.api.endpoints['host'].list(**kwargs))
            elif ns.contextual_noun == "volume":
                self.output(self.api.endpoints['volume'].list(**kwargs))
        except AttributeError:
            self.output(self.api_endpoint.list())

    def _resolve_mgt(self, ns):
        if ns.mgt is None:
            raise BadUserInput("No MGT supplied.")

        if len(ns.mgt) > 1:
            raise BadUserInput("Only 1 MGT per filesystem is allowed.")

        mgt = {}
        try:
            mgt_vn = self._resolve_volume_node(ns.mgt[0])
            mgt['volume_id'] = mgt_vn.volume_id
        except (InvalidVolumeNode, NotFound):
            mgs = self.api.endpoints['host'].show(ns.mgt[0])
            kwargs = {'host_id': mgs['id'], 'kind': 'mgt'}
            try:
                mgt['id'] = self.api.endpoints['target'].list(**kwargs)[0]['id']
            except IndexError:
                raise BadUserInput("Invalid mgt spec: %s" % ns.mgt[0])
        return mgt

    def _resolve_mdt(self, ns):
        if ns.mdts is None:
            raise BadUserInput("No MDT supplied.")

        if len(ns.mdts) > 1:
            # NB: Following the API -- only 1 MDT supported for now.
            raise BadUserInput("Only 1 MDT per filesystem is supported.")

        mdt_vn = self._resolve_volume_node(ns.mdts[0])
        return {'conf_params': {}, 'volume_id': mdt_vn.volume_id}

    def _resolve_osts(self, ns):
        if ns.osts is None:
            raise BadUserInput("At least one OST must be supplied.")

        osts = []
        for ost_spec in ns.osts:
            ost_vn = self._resolve_volume_node(ost_spec)
            osts.append({'conf_params': {}, 'volume_id': ost_vn.volume_id})
        return osts

    def add(self, ns):
        # TODO: Adjust primary/failover relationships via CLI
        kwargs = {'conf_params': {}}
        kwargs['name'] = ns.subject
        kwargs['mgt'] = self._resolve_mgt(ns)
        kwargs['mdt'] = self._resolve_mdt(ns)
        kwargs['osts'] = self._resolve_osts(ns)
        self.output(self.api_endpoint.create(**kwargs))

    def mountspec(self, ns):
        fs = self.api_endpoint.show(ns.subject)
        self.output(fs['mount_path'])


class TargetHandler(Handler):
    nouns = ["target", "tgt", "mgt", "mdt", "ost"]
    verbs = ["list", "show", "add", "remove", "start", "stop", "failover", "failback"]

    def __init__(self, *args, **kwargs):
        super(TargetHandler, self).__init__(*args, **kwargs)
        self.api_endpoint = self.api.endpoints['target']

    def failover(self, ns):
        target = self.api.endpoints['target'].show(ns.subject)
        kwargs = {
            'jobs': [{'class_name': "FailoverTargetJob",
                      'args': {'target_id': target.id}}],
            'message': "Failing %s over to secondary" % target.label
        }
        self.output(self.api.endpoints['command'].create(**kwargs))

    def failback(self, ns):
        target = self.api.endpoints['target'].show(ns.subject)
        kwargs = {
            'jobs': [{'class_name': "FailbackTargetJob",
                      'args': {'target_id': target.id}}],
            'message': "Failing %s back to primary" % target.label
        }
        self.output(self.api.endpoints['command'].create(**kwargs))

    def stop(self, ns):
        kwargs = {'state': "unmounted"}
        self.output(self.api_endpoint.update(ns.subject, **kwargs))

    def start(self, ns):
        kwargs = {'state': "mounted"}
        self.output(self.api_endpoint.update(ns.subject, **kwargs))

    def remove(self, ns):
        # HTTP DELETE doesn't seem to work -- some downcasting problem?
        kwargs = {'state': "removed"}
        self.output(self.api_endpoint.update(ns.subject, **kwargs))

    def add(self, ns):
        vn = self._resolve_volume_node(ns.subject)
        kwargs = {'kind': ns.noun.upper(), 'volume_id': vn.volume_id}
        if ns.noun != 'mgt':
            fs = self.api.endpoints['filesystem'].show(ns.filesystem)
            kwargs['filesystem_id'] = fs.id

        self.output(self.api_endpoint.create(**kwargs))

    def list(self, ns):
        kwargs = {'limit': '0'}  # api defaults to 20
        if ns.noun in ["mgt", "mdt", "ost"]:
            kwargs['kind'] = ns.noun
        self.output(self.api_endpoint.list(**kwargs))


class VolumeHandler(Handler):
    nouns = ["volume", "vol"]
    verbs = ["list", "show"]

    def __init__(self, *args, **kwargs):
        super(VolumeHandler, self).__init__(*args, **kwargs)
        self.api_endpoint = self.api.endpoints['volume']


class NidsHandler(Handler):
    nouns = ["nid"]
    verbs = ["update", "relearn"]
    intransitive_verbs = ["update"]

    def update(self, ns):
        kwargs = {'message': "Updating filesystem NID configuration",
                  'jobs': [{'class_name': 'UpdateNidsJob', 'args': {}}]}
        self.output(self.api.endpoints['command'].create(**kwargs))

    def relearn(self, ns):
        host = self.api.endpoints['host'].show(ns.subject)
        kwargs = {'message': "Relearning NIDs on %s" % host.label,
                  'jobs': [{'class_name': 'RelearnNidsJob', 'args': {
                      'host_id': host['id']
        }}]}
        self.output(self.api.endpoints['command'].create(**kwargs))


class ConfigHandler(Handler):
    nouns = ["configuration", "cfg"]
    verbs = ["dump", "load"]
    intransitive_verbs = ["dump"]

    def dump(self, ns):
        import json
        response = self.api.endpoints['configuration'].get_decoded()
        print json.dumps(response, indent=4)

    def load(self, ns):
        import json
        config = json.load(open(ns.subject, "r"))
        self.api.endpoints['configuration'].create(**config)
