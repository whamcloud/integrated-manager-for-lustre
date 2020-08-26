#! /usr/bin/python

import fileinput
import re


def natural_sort_key(s, _nsre=re.compile("([0-9]+)")):
    return [int(text) if text.isdigit() else text.lower() for text in _nsre.split(s)]


devices = {}
for line in fileinput.input():
    items = line.split()
    devices[items[4][1:]] = items[1][1:-1]

bindings = [
    "mpath{} {}".format(chr(ord("a") + int(x[3:]) - 1), devices[x])
    for x in sorted(devices.keys(), key=natural_sort_key)
    if x.find("ost") >= 0
]
extras = filter(lambda x: x.find("ost") == -1, devices.keys())
extras = ["mpath{} {}".format(chr(ord("a") + int(i + len(bindings))), devices[x]) for (i, x) in enumerate(extras)]

bindings = bindings + extras

print "Writing bindings file."
print bindings

f = open("/etc/multipath/bindings", "w")
f.write("\n".join(bindings))
f.close()
