#!/usr/bin/env python

import sys

bytes = (open(sys.argv[1]).read())
try:
    ustr = unicode(bytes, 'utf-8', errors='strict')
    sys.exit(0)
except UnicodeDecodeError, e:
    print "File %s is not valid UTF-8: %s" % (sys.argv[1], e)
    sys.exit(-1)
