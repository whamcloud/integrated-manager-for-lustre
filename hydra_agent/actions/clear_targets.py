
import glob
import os

from targets import _stop_target, _unconfigure_ha, list_ha_targets

def clear_targets(args):
    for resource in list_ha_targets(args):
        (label, serial) = resource.split("_")
        print "%s\n%s" % (label, len(label) * "=")
        try:
            print "Stopping"
            _stop_target(label, serial)
        except Exception,e:
            pass
        try:
            print "Unconfiguring"
            _unconfigure_ha(False, label, serial)
            _unconfigure_ha(True, label, serial)
        except Exception,e:
            pass

