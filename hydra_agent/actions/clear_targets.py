# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from hydra_agent.plugins import AgentPlugin
from hydra_agent.actions.targets import _stop_target, _unconfigure_ha, list_ha_targets


def clear_targets(args):
    for resource in list_ha_targets(args):
        (label, serial) = resource.split("_")
        print "%s\n%s" % (label, len(label) * "=")
        try:
            print "Stopping"
            _stop_target(label, serial)
        except Exception:
            pass
        try:
            print "Unconfiguring"
            _unconfigure_ha(False, label, serial)
            _unconfigure_ha(True, label, serial)
        except Exception:
            pass


class ClearTargetPlugin(AgentPlugin):
    def register_commands(self, parser):
        p = parser.add_parser("clear-targets",
                              help="clear targets from HA config")
        p.set_defaults(func=clear_targets)
