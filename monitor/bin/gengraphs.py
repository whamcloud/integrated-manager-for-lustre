#!/usr/bin/env python
from django.core.management import setup_environ
import settings
setup_environ(settings)

from monitor.models import *
import rrdtool
import time
import os, sys, fcntl
from cStringIO import StringIO

def do_ost_graph(name):
    topdir = "/var/lib/cerebro"
    rrd = "%s/rrds/target/%s.rrd" % (topdir, name)
    graph = "%s/graphs/target/%s.png" % (topdir, name)
    args = [
        graph,
        "--start", "%d" % (time.time() - 600),
        "--width", "250",
        "DEF:read_bytes=%s:read_bytes:AVERAGE" % rrd,
        "DEF:write_bytes=%s:write_bytes:AVERAGE" % rrd,
        "LINE2:read_bytes#ff0000:read bytes/sec",
        "LINE2:write_bytes#0000ff:write bytes/sec"
    ]
    rrdtool.graph([(a.encode('ascii')) for a in args])
    #so, sys.stdout = sys.stdout, StringIO()
    r, w = os.pipe()
    fcntl.fcntl(r, fcntl.F_SETFL, os.O_NONBLOCK)
    so = os.dup(sys.stdout.fileno())
    os.dup2(w, 1)
    args[0] = "-"
    #f = open("/tmp/%s.png" % name, "w")
    rrdtool.graph([(a.encode('ascii')) for a in args])
    buf = StringIO()
    i = 0
    while i < 2:
        try:
            chunk = os.read(r, 1024)
            if chunk:
                buf.write(chunk)
            else:
                break
        except OSError, e:
            sys.stdout.flush()
            i += 1
            time.sleep(1)
            continue

    os.dup2(so, 1)
    f = open("/var/lib/cerebro/graphs/target/buf-%s.png" % name, "w")
    f.write(buf.getvalue())
    f.close()
    os.close(r)
    os.close(w)
    #sys.stdout = so

def do_target_graphs(filesystem):
    osts = ObjectStoreTarget.objects.filter(filesystem = filesystem)
    for ost in osts:
        do_ost_graph(ost.name)

def do_server_graph(hostname):
    topdir = "/var/lib/cerebro"
    rrd = "%s/rrds/server/%s.rrd" % (topdir, hostname)
    graph = "%s/graphs/server/%s.png" % (topdir, hostname)
    args = [
        graph,
        "--title", hostname,
        "--start", "%d" % (time.time() - 600),
        "--only-graph",
        "DEF:pct_cpu=%s:pct_cpu:AVERAGE" % rrd,
        "DEF:pct_mem=%s:pct_mem:AVERAGE" % rrd,
        "LINE2:pct_cpu#ff0000",
        "LINE2:pct_mem#0000ff"
    ]
    #rrdtool.graph([(a.encode('ascii')) for a in args])

def do_server_graphs(filesystem):
    servers = Host.objects.all()
    for server in servers:
        do_server_graph(server.address)

def do_graphs():
    for filesystem in Filesystem.objects.all():
        do_target_graphs(filesystem)
        do_server_graphs(filesystem)

if __name__ == '__main__':
    while True:
        do_graphs()
        sys.exit(0)
        time.sleep(5)
