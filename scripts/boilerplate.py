#!/usr/bin/env python
#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import sys
import re

OLD_BOILERPLATE = """# Copyright \d{4} Whamcloud"""

PYTHON_BOILERPLATE = """#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


"""


def apply_boilerplate(filename):
    if filename.endswith(".py"):
        lines = open(filename, 'r').readlines()
        if not lines:
            return

        insert_at = 0
        try:
            while lines[insert_at].startswith("#!") or lines[insert_at].startswith("# vim:"):
                insert_at += 1
        except IndexError:
            # Nothing but a header
            return

        cursor = insert_at
        try:
            while lines[cursor][0] == '#' or lines[cursor].strip() == "":
                cursor += 1
        except IndexError:
            # Overran file before finding non-whitespace, it's not code
            return
        lines = lines[0:insert_at] + lines[cursor:]

        output = "".join(lines[0:insert_at]) + PYTHON_BOILERPLATE + "".join(lines[insert_at:])
        open(filename, 'w').write(output)
    else:
        raise NotImplementedError("Unknown extension")


def has_boilerplate(filename):
    if filename.endswith(".py"):
        text = open(filename, 'r').read()
        if not text.strip():
            return True

        try:
            text.index(PYTHON_BOILERPLATE)
            return True
        except ValueError:
            lines = [l for l in open(filename, 'r').readlines() if not (l.startswith("#") or l.strip() == "")]
            if lines:
                return False
            else:
                return True
    else:
        raise NotImplementedError("Unknown extension")


def freshen_boilerplate(filename):
    if filename.endswith(".py"):
        text = open(filename, 'r').read()
        match = re.search(OLD_BOILERPLATE, text)
        if match:
            apply_boilerplate(filename)
    else:
        raise NotImplementedError("Unknown extension")

try:
    command = sys.argv[1]
    filename = sys.argv[2]
except IndexError:
    print "Usage: boilerplate.py <test|apply> <filename>"
    sys.exit(-1)
if command == 'apply':
    apply_boilerplate(filename)
elif command == 'freshen':
    freshen_boilerplate(filename)
elif command == 'test':
    has = has_boilerplate(filename)
    if not has:
        print "Missing copyright boilerplate"
        sys.exit(-2)
else:
    print "Unknown command %s" % command
    sys.exit(-1)
