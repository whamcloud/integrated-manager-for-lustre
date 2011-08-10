#!/usr/bin/python

import os
import sys

# Extra deps not expressed in lsmod's list of dependent modules
extra_deps = {"lquota": set(["lov", "osc", "mgc", "mds", "mdc", "lmv"])}

class Module:
    def __init__(self, lsmod_line):
        parts = lsmod_line.split()
        self.name = parts[0]
        depcount = int(parts[2])
        try:
            self.dependents = set(parts[3].split(","))
        except IndexError:
            self.dependents = set([])
        #if depcount != len(self.dependents): 
        #    print "Non-module dependencies on %s" % self.name
        #    sys.exit(-1)
        

def load_lsmod():
    modules = {}

    lines = os.popen("/sbin/lsmod").read().split("\n")[1:-1]
    for line in lines:
        m = Module(line.strip())
        modules[m.name] = m

    for name,module in modules.items():
        try:
            module.dependents |= (extra_deps[name] & set(modules.keys()))
        except KeyError:
            pass

    return modules

def remove_module(name, modules):
    try:
        m = modules[name]
    except KeyError:
        # It's not loaded, do nothing.
        return
    print "Removing %d dependents of %s : %s" % (len(m.dependents), name, m.dependents)
    while (len(m.dependents) > 0):
        remove_module(m.dependents.pop(), modules)

    print "Removing %s" % name
    rc = os.system("rmmod %s" % name)
    if rc != 0:
        raise "Failed to rmmod '%s'" % name

    modules.pop(name)
    for m in modules.values():
        if name in m.dependents:
            m.dependents.remove(name)

modules = load_lsmod()
remove_module(sys.argv[1], modules)
