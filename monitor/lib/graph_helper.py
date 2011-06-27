import time
import re
import os, sys, fcntl
import rrdtool
from cStringIO import StringIO

def load_graph(name):
    image_type = "png"
    graph_dir = "/var/lib/cerebro/graphs"
    graph_path = "%s/%s.%s" % (graph_dir, name, image_type)
    image_data = open(graph_path, "rb").read()
    return image_data, "image/%s" % image_type

def dyn_load_graph(subdir, name):
    image_type = "png"
    rrd = "/var/lib/cerebro/rrds/%s.rrd" % name
    args = [
        "-",
        "--start", "%d" % (time.time() - 600),
        "--width", "250",
    ]

    if subdir == "target":
        if re.search("MDT", name):
            args.extend([
                "DEF:kbytes_free=%s:kbytes_free:AVERAGE" % rrd,
                "DEF:inodes_free=%s:inodes_free:AVERAGE" % rrd,
                "LINE2:kbytes_free#ff0000:free kbytes",
                "LINE2:inodes_free#0000ff:free inodes"
            ])
        else:
            args.extend([
                "DEF:read_bytes=%s:read_bytes:AVERAGE" % rrd,
                "DEF:write_bytes=%s:write_bytes:AVERAGE" % rrd,
                "LINE2:read_bytes#ff0000:read bytes/sec",
                "LINE2:write_bytes#0000ff:write bytes/sec"
            ])
    elif subdir == "server":
        args.extend([
                    "DEF:pct_cpu=%s:pct_cpu:AVERAGE" % rrd,
                    "DEF:pct_mem=%s:pct_mem:AVERAGE" % rrd,
                    "LINE2:pct_cpu#ff0000:% cpu used",
                    "LINE2:pct_mem#0000ff:% ram used"
        ])
    
    r, w = os.pipe()
    fcntl.fcntl(r, fcntl.F_SETFL, os.O_NONBLOCK)
    so = os.dup(sys.stdout.fileno())
    os.dup2(w, 1)
    rrdtool.graph([(a.encode('ascii')) for a in args])
    image_data = StringIO()
    i = 0
    while i < 2:
        try:
            chunk = os.read(r, 1024)
            if chunk:
                image_data.write(chunk)
            else:
                break
        except OSError, e:
            sys.stdout.flush()
            i += 1
            time.sleep(0.25)
            continue

    os.dup2(so, 1)
    os.close(r)
    os.close(w)
    return image_data.getvalue(), "image/%s" % image_type
