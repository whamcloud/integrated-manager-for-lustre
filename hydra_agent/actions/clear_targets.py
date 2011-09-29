
import glob
import os
from hydra_agent.store import LIBDIR

from targets import _stop_target, _unconfigure_ha

def clear_targets(args):
    for p in glob.glob(os.path.join(LIBDIR, "*")):
        label = os.path.split(p)[1]
        print "%s\n%s" % (label, len(label) * "=")
        try:
            print "Stopping"
            _stop_target(label)
        except Exception,e:
            pass
        try:
            print "Unconfiguring"
            _unconfigure_ha(True, label)
        except Exception,e:
            pass

