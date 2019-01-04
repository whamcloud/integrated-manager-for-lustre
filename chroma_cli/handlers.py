# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from itertools import product
from functools import partial
from argparse import REMAINDER, SUPPRESS

from chroma_cli.output import StandardFormatter
from chroma_cli.api import CommandMonitor
from chroma_cli.exceptions import (
    InvalidVolumeNode,
    TooManyMatches,
    BadUserInput,
    NotFound,
    StateChangeConfirmationRequired,
    JobConfirmationRequired,
    InvalidStateChange,
    InvalidJobError,
    ReformatVolumesConfirmationRequired,
)


class Dispatcher(object):
    def __init__(self):
        self._build_handler_map()

    def _build_handler_map(self):
        self.handlers = {}
        # NB: This only handles a single level of subclasses.
        for cls in Handler.__subclasses__():
            name = cls.nouns[0]
            if name in self.handlers:
                raise RuntimeError("Handler collision: %s:%s -> %s:%s" % (cls, name, self.handlers[name], name))
            else:
                self.handlers[name] = {}
                self.handlers[name]["klass"] = cls
                self.handlers[name]["aliases"] = cls.nouns[1:]
                self.handlers[name]["verbs"] = cls.verbs

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
                if noun in handler["aliases"]:
                    handler_name = name
                    break
            if handler_name == noun:
                return noun, None

        try:
            if ns.args[0] in self.handlers[handler_name]["verbs"]:
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
            noun_parser = subparsers.add_parser(key, aliases=handler["aliases"], help=", ".join(handler["verbs"]))
            noun_parser.set_defaults(handler=handler["klass"])

            verb_subparsers = noun_parser.add_subparsers()
            intransitive = handler["klass"].intransitive_verbs
            irregular = handler["klass"].irregular_verbs

            for verb in handler["verbs"]:
                if verb not in intransitive + irregular:
                    verb_parser = verb_subparsers.add_parser(verb, help="%s a %s" % (verb, key))
                    verb_parser.add_argument("subject", metavar=key)
                    if "verb" in ns and ns.verb == "add":
                        # Special-case for "add"... It wants to do its
                        # own parsing in the handler.
                        verb_parser.add_argument("args", nargs=REMAINDER)
                elif verb in intransitive:
                    verb_parser = verb_subparsers.add_parser(verb, help="%s all %ss" % (verb, key))
                else:
                    # This should be fine until it's not.
                    verb_parser = verb_subparsers.add_parser(verb, help="%s for %s" % (verb, key))
                    verb_parser.add_argument("subject", metavar=key)

                verb_parser.set_defaults(handler=handler["klass"])
                handler["klass"].add_args(verb_parser, verb, noun)

            if len(handler["klass"].contextual_actions()) > 0:
                ctx_parser = verb_subparsers.add_parser(
                    "context", help="%s_name action (e.g. ost-list, vol-list, etc.)" % key
                )
                ctx_parser.add_argument("subject", metavar=key)
                ctx_subparsers = ctx_parser.add_subparsers()
                for action in handler["klass"].contextual_actions():
                    ctx_act_parser = ctx_subparsers.add_parser(action, help="run %s in the %s context" % (action, key))
                    ctx_act_parser.add_argument(
                        "--primary", action="store_true", help="Restrict list to primaries only"
                    )
                    ctx_act_parser.set_defaults(handler=handler["klass"], contextual_action=action)


class Handler(object):
    nouns = []
    contextual_nouns = []
    job_map = {}
    verbs = ["show", "list", "add", "remove"]
    intransitive_verbs = ["list"]
    irregular_verbs = []

    @classmethod
    def contextual_actions(cls):
        # Really, the only verb that makes sense in general context is list
        return ["%s-%s" % t for t in product(*[cls.contextual_nouns, ["list"]])]

    @classmethod
    def add_args(cls, parser, verb, noun=None):
        "Add custom arguments for given verb."
        pass

    def __init__(self, api, formatter=None):
        self.api = api

        self.output = formatter
        if not self.output:
            self.output = StandardFormatter()

        self.errors = []

        for verb, job_class in self.job_map.items():
            setattr(self, verb, partial(self._run_advertised_job, job_class))

    def __call__(self, parser, ns, args=None):
        try:
            ns.contextual_noun, ns.verb = ns.contextual_action.split("-")
        except AttributeError:
            pass

        if "verb" in ns and ns.verb == "add":
            parser.reset()
            self._api_fields_to_parser_args(parser, add_help=True)
            ns = parser.parse_args(ns.args, ns)

        verb_method = getattr(self, ns.verb)
        verb_method(ns)

    def _run_advertised_job(self, job_class, ns):
        subject = self.api_endpoint.show(ns.subject)
        try:
            job = [j for j in subject["available_jobs"] if j["class_name"] == job_class][0]
        except IndexError:
            raise InvalidJobError(job_class, [j["class_name"] for j in subject["available_jobs"]])

        if job["confirmation"] and not ns.force:
            raise JobConfirmationRequired(ns.verb, ns.subject, job["confirmation"])

        kwargs = {"jobs": [job], "message": "%s created by CLI" % job["class_name"]}
        self.output(self.api.endpoints["command"].create(**kwargs))

    def _api_fields_to_parser_args(self, parser, add_help=False):
        if add_help:
            parser.add_argument("--help", "-h", help="show this help message and exit", default=SUPPRESS, action="help")
        for name, attrs in self.api_endpoint.fields.items():
            if attrs["readonly"]:
                continue

            kwargs = {"help": attrs["help_text"]}
            if attrs["type"] in ["related", "list"]:
                kwargs["action"] = "append"
                kwargs["type"] = str
            elif attrs["type"] == "boolean":
                kwargs["action"] = "store_true"
                kwargs["default"] = False
            elif attrs["type"] == "integer":
                kwargs["type"] = int

            parser.add_argument("--%s" % name, **kwargs)

    def _resolve_volume_node(self, spec):
        try:
            hostname, path = spec.split(":")
            host = self.api.endpoints["host"].show(hostname)
            kwargs = {"host": host["id"], "path": path}
            vn_set = self.api.endpoints["volume_node"].list(**kwargs)
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

    def list(self, ns, endpoint=None, **kwargs):
        kwargs["limit"] = "0"  # api defaults to 20
        if not endpoint:
            endpoint = self.api_endpoint
        self.output(endpoint.list(**kwargs))

    def show(self, ns, endpoint=None):
        if not endpoint:
            endpoint = self.api_endpoint
        self.output(endpoint.show(ns.subject))

    def remove(self, ns, endpoint=None):
        if not endpoint:
            endpoint = self.api_endpoint
        self.change_state(ns.subject, "removed", ns.force)

    def change_state(self, subject, end_state, force=False):
        available_states = [t["state"] for t in self.api_endpoint.show(subject)["available_transitions"]]

        if end_state not in available_states:
            raise InvalidStateChange(end_state, available_states)

        if not force:
            report = self.api_endpoint.update(subject, state=end_state, dry_run=True)
            if report and (
                any(j["requires_confirmation"] for j in report["dependency_jobs"])
                or report["transition_job"]["requires_confirmation"]
            ):
                raise StateChangeConfirmationRequired(report)

        self.output(self.api_endpoint.update(subject, state=end_state))


class ServerHandler(Handler):
    nouns = ["server", "srv", "mgs", "mds", "oss"]
    job_map = {
        "reboot": "RebootHostJob",
        "shutdown": "ShutdownHostJob",
        "poweroff": "PoweroffHostJob",
        "poweron": "PoweronHostJob",
        "powercycle": "PowercycleHostJob",
        "force_remove": "ForceRemoveHostJob",
    }
    verbs = ["show", "list", "add", "remove"] + job_map.keys()
    contextual_nouns = ["target", "tgt", "mgt", "mdt", "ost", "volume", "vol"]

    def __init__(self, *args, **kwargs):
        super(ServerHandler, self).__init__(*args, **kwargs)
        self.api_endpoint = self.api.endpoints["host"]

    def list(self, ns, endpoint=None, **kwargs):
        try:
            host = self.api_endpoint.show(ns.subject)
            kwargs["host_id"] = host["id"]
            if "primary" in ns and ns.primary:
                kwargs["primary"] = True

            if ns.contextual_noun in ["ost", "mdt", "mgt"]:
                kwargs["kind"] = ns.contextual_noun
                endpoint = self.api.endpoints["target"]
            elif ns.contextual_noun in ["target", "tgt"]:
                endpoint = self.api.endpoints["target"]
            elif ns.contextual_noun in ["volume", "vol"]:
                endpoint = self.api.endpoints["volume"]
        except AttributeError:
            if ns.noun in ["mgs", "mds", "oss"]:
                kwargs["role"] = ns.noun
            endpoint = self.api_endpoint

        super(ServerHandler, self).list(ns, endpoint, **kwargs)

    def test_host(self, ns, endpoint=None, **kwargs):
        failure_text = {
            "auth": "The manager was unable to login to %s on your behalf",
            "agent": "The manager was unable to invoke the agent on %s",
            "resolve": "Unable to resolve fqdn for %s",
            "reverse_resolve": "The agent on %s was unable to resolve the manager's IP address",
            "ping": "The manager was unable to ping %s",
            "reverse_ping": "The agent on %s was unable to ping the manager's IP address",
            "hostname_valid": "The system hostname on %s either does not resolve, or resolves to a loopback address",
            "fqdn_resolves": "The self-reported fqdn on %s does not resolve on the manager",
            "fqdn_matches": "The self-reported fqdn on %s does not resolve to the same address as the hostname supplied via CLI",
            "yum_valid_repos": "The yum configuration on %s contains invalid repository entries",
            "yum_can_update": "Unable to verify that %s is able to access any yum mirrors for vendor packages",
            "openssl": "Unable to verify that OpenSSL is working as expected for %s",
        }

        command = self.api.endpoints["test_host"].create(**kwargs)
        self.output.command(command)

        # Actually the command above may just return if the user used nowait so we need to make sure that the command has really
        # completed and if not wait for it to complete.
        command = CommandMonitor(self.api, command).wait_complete()

        if command["cancelled"]:
            raise BadUserInput("\nTest host connection command cancelled for %s" % kwargs["address"])
        elif command["errored"]:
            raise BadUserInput("\nTest host connection command errored for %s" % kwargs["address"])

        job = self.api.endpoints["job"].get_decoded(command["jobs"][0])
        step_result = job["step_results"].values()[0]

        failures = []
        for failkey in [result["name"] for result in step_result["status"] if not result["value"]]:
            failures.append(failure_text[failkey] % step_result["address"])

        if failures:
            message = "Failed sanity checks (use --force to add anyway): "
            raise BadUserInput("\n".join([message] + failures))

    def add(self, ns):
        kwargs = {"address": ns.subject}

        if not ns.server_profile:
            raise BadUserInput("No server_profile supplied.")

        kwargs["server_profile"] = self.api.endpoints["server_profile"].show(ns.server_profile[0])["resource_uri"]

        if not ns.force:
            self.test_host(ns, **kwargs)
        self.output(self.api_endpoint.create(**kwargs))


class LNetConfigurationHandler(Handler):
    nouns = ["lnet_configuration"]
    verbs = []
    intransitive_verbs = []

    lnet_actions = ["lnet-stop", "lnet-start", "lnet-load", "lnet-unload"]

    @classmethod
    def contextual_actions(cls):
        return cls.lnet_actions + super(LNetConfigurationHandler, cls).contextual_actions()

    def __init__(self, *args, **kwargs):
        super(LNetConfigurationHandler, self).__init__(*args, **kwargs)
        self.api_endpoint = self.api.endpoints["lnet_configuration"]

        for action in self.lnet_actions:
            # NB: This will break if we ever want to add more secondary
            # actions with the same verbs to this handler.
            verb = action.split("-")[1]
            self.__dict__[verb] = self.set_lnet_state

    def set_lnet_state(self, ns):
        lnet_state = {"stop": "lnet_down", "start": "lnet_up", "unload": "lnet_unloaded", "load": "lnet_down"}
        self.change_state(ns.subject, lnet_state[ns.verb], ns.force)


class ServerProfileHandler(Handler):
    nouns = ["server_profile"]
    verbs = ["list"]
    intransitive_verbs = ["list"]

    def __init__(self, *args, **kwargs):
        super(ServerProfileHandler, self).__init__(*args, **kwargs)
        self.api_endpoint = self.api.endpoints["server_profile"]


class FilesystemHandler(Handler):
    nouns = ["filesystem", "fs"]
    contextual_nouns = ["target", "tgt", "mgt", "mdt", "ost", "volume", "vol", "server", "mgs", "mds", "oss"]
    verbs = ["list", "show", "add", "remove", "start", "stop", "detect", "mountspec"]
    intransitive_verbs = ["list", "detect"]
    irregular_verbs = ["mountspec"]

    @classmethod
    def add_args(cls, parser, verb, noun=None):
        if verb == "add":
            parser.add_argument("--reformat", action="store_true", help="reformat volumes without prompting")

    def __init__(self, *args, **kwargs):
        super(FilesystemHandler, self).__init__(*args, **kwargs)
        self.api_endpoint = self.api.endpoints["filesystem"]

    def stop(self, ns):
        self.change_state(ns.subject, "stopped", ns.force)

    def start(self, ns):
        self.change_state(ns.subject, "available", ns.force)

    def detect(self, ns):
        kwargs = {"message": "Detecting filesystems", "jobs": [{"class_name": "DetectTargetsJob", "args": {}}]}
        self.output(self.api.endpoints["command"].create(**kwargs))

    def list(self, ns, endpoint=None, **kwargs):
        try:
            fs = self.api_endpoint.show(ns.subject)
            kwargs["filesystem_id"] = fs["id"]

            if ns.contextual_noun in ["ost", "mdt", "mgt"]:
                kwargs["kind"] = ns.contextual_noun
                endpoint = self.api.endpoints["target"]
            elif ns.contextual_noun == "target":
                endpoint = self.api.endpoints["target"]
            elif ns.contextual_noun == "server":
                endpoint = self.api.endpoints["host"]
            elif ns.contextual_noun in ["oss", "mds", "mgs"]:
                kwargs["role"] = ns.contextual_noun
                endpoint = self.api.endpoints["host"]
            elif ns.contextual_noun == "volume":
                endpoint = self.api.endpoints["volume"]
        except AttributeError:
            endpoint = self.api_endpoint

        super(FilesystemHandler, self).list(ns, endpoint, **kwargs)

    def _resolve_mgt(self, ns):
        if ns.mgt is None:
            raise BadUserInput("No MGT supplied.")

        if len(ns.mgt) > 1:
            raise BadUserInput("Only 1 MGT per filesystem is allowed.")

        mgt = {}
        try:
            mgt_vn = self._resolve_volume_node(ns.mgt[0])
            mgt["volume_id"] = mgt_vn.volume_id
        except (InvalidVolumeNode, NotFound):
            mgs = self.api.endpoints["host"].show(ns.mgt[0])
            kwargs = {"host_id": mgs["id"], "kind": "mgt"}
            try:
                mgt["id"] = self.api.endpoints["target"].list(**kwargs)[0]["id"]
            except IndexError:
                raise BadUserInput("Invalid mgt spec: %s" % ns.mgt[0])
        return mgt

    def _resolve_mdts(self, ns):
        if ns.mdts is None:
            raise BadUserInput("At least one MDT must be supplied.")

        mdts = []
        for mdt_spec in ns.mdts:
            mdt_vn = self._resolve_volume_node(mdt_spec)
            mdts.append({"conf_params": {}, "volume_id": mdt_vn.volume_id})
        return mdts

    def _resolve_osts(self, ns):
        if ns.osts is None:
            raise BadUserInput("At least one OST must be supplied.")

        osts = []
        for ost_spec in ns.osts:
            ost_vn = self._resolve_volume_node(ost_spec)
            osts.append({"conf_params": {}, "volume_id": ost_vn.volume_id})
        return osts

    def add(self, ns):
        # TODO: Adjust primary/failover relationships via CLI
        kwargs = {"conf_params": {}}
        kwargs["name"] = ns.subject
        kwargs["mgt"] = self._resolve_mgt(ns)
        kwargs["mdts"] = self._resolve_mdts(ns)
        kwargs["osts"] = self._resolve_osts(ns)

        formatted_volumes = []
        for target in [kwargs["mgt"]] + kwargs["mdts"] + kwargs["osts"]:
            # Skip resolved MGS host
            if "volume_id" not in target:
                continue

            if ns.reformat:
                target["reformat"] = True
            else:
                volume = self.api.endpoints["volume"].show(target["volume_id"])
                if volume["filesystem_type"]:
                    formatted_volumes.append(volume)

        if formatted_volumes:
            # Bit of a hack -- let these be rebuilt from args on the next
            # pass. Otherwise we get duplicates and that makes the API sad.
            for attr in ["mgt", "mdts", "osts"]:
                delattr(ns, attr)
            raise ReformatVolumesConfirmationRequired(formatted_volumes)

        self.output(self.api_endpoint.create(**kwargs))

    def mountspec(self, ns):
        fs = self.api_endpoint.show(ns.subject)
        self.output(fs["mount_path"])


class TargetHandler(Handler):
    nouns = ["target", "tgt", "mgt", "mdt", "ost"]
    job_map = {"failover": "FailoverTargetJob", "failback": "FailbackTargetJob"}
    verbs = ["list", "show", "add", "remove", "start", "stop"] + job_map.keys()

    @classmethod
    def add_args(cls, parser, verb, noun=None):
        if verb == "add":
            parser.add_argument("--reformat", action="store_true", help="reformat volume without prompting")
            if noun and noun != "mgt":
                parser.add_argument("--filesystem", required=True, help="filesystem to which target is being added")

    def __init__(self, *args, **kwargs):
        super(TargetHandler, self).__init__(*args, **kwargs)
        self.api_endpoint = self.api.endpoints["target"]

    def stop(self, ns):
        self.change_state(ns.subject, "unmounted", ns.force)

    def start(self, ns):
        self.change_state(ns.subject, "mounted", ns.force)

    def add(self, ns):
        vn = self._resolve_volume_node(ns.subject)
        volume = self.api.endpoints["volume"].show(vn.volume_id)

        kwargs = {"kind": ns.noun.upper(), "volume_id": vn.volume_id}
        if ns.noun != "mgt":
            fs = self.api.endpoints["filesystem"].show(ns.filesystem)
            kwargs["filesystem_id"] = fs.id
        if ns.reformat:
            kwargs["reformat"] = True
        else:
            if volume["filesystem_type"]:
                raise ReformatVolumesConfirmationRequired([volume])

        self.output(self.api_endpoint.create(**kwargs))

    def list(self, ns, endpoint=None, **kwargs):
        if ns.noun in ["mgt", "mdt", "ost"]:
            kwargs["kind"] = ns.noun
        endpoint = self.api_endpoint

        super(TargetHandler, self).list(ns, endpoint, **kwargs)


class VolumeHandler(Handler):
    nouns = ["volume", "vol"]
    verbs = ["list", "show"]

    def __init__(self, *args, **kwargs):
        super(VolumeHandler, self).__init__(*args, **kwargs)
        self.api_endpoint = self.api.endpoints["volume"]

    @classmethod
    def add_args(cls, parser, verb, noun=None):
        if verb == "list":
            parser.add_argument("--all", action="store_true", help="list all volumes")

    def list(self, ns, endpoint=None, **kwargs):
        if not ns.all:
            kwargs["category"] = "usable"
        Handler.list(self, ns, endpoint, **kwargs)


class NidsHandler(Handler):
    nouns = ["nid"]
    verbs = ["update", "relearn"]
    intransitive_verbs = ["update"]

    def update(self, ns):
        kwargs = {
            "message": "Updating file system NID configuration",
            "jobs": [{"class_name": "UpdateNidsJob", "args": {}}],
        }
        self.output(self.api.endpoints["command"].create(**kwargs))

    def relearn(self, ns):
        # Relearn really makes no sense now, the nids are always known, but this keeps compatibility
        host = self.api.endpoints["host"].show(ns.subject)
        kwargs = {
            "message": "Updating device info on %s" % host.label,
            "jobs": [{"class_name": "UpdateDevicesJob", "args": {"hosts": [host]}}],
        }
        self.output(self.api.endpoints["command"].create(**kwargs))
