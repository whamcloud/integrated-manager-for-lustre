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

def dyn_load_graph(subdir, name, graph_type, size):
    image_type = "png"
    rrd = "/var/lib/cerebro/rrds/%s.rrd" % name
    args = [
        "-",
        "--start", "%d" % (time.time() - 600),
        "--width", "250",
    ]

    if subdir == "target":
        if re.search("MDT", name):
            if graph_type == "space":
                args.extend([
                    "DEF:kbytes_free=%s:kbytes_free:AVERAGE" % rrd,
                    "LINE2:kbytes_free#ff0000:free kbytes",
                ])
            elif graph_type == "inodes":
                args.extend([
                    "DEF:inodes_free=%s:inodes_free:AVERAGE" % rrd,
                    "LINE2:inodes_free#0000ff:free inodes"
                ])
        else:
            if graph_type == "ops":
                args.extend([
                    "DEF:iops=%s:iops:AVERAGE" % rrd,
                    "LINE2:iops#00ff00:iops"
                ])
            elif graph_type == "lock":
                args.extend([
                    "DEF:grant_rate=%s:grant_rate:AVERAGE" % rrd,
                    "DEF:cancel_rate=%s:cancel_rate:AVERAGE" % rrd,
                    "LINE2:grant_rate#fc0000:lock grants/s",
                    "LINE2:cancel_rate#00fc00:lock cancels/s"
                ])
            elif graph_type == "clients":
                args.extend([
                    "DEF:num_exports=%s:num_exports:AVERAGE" % rrd,
                    "LINE2:num_exports#0000fb:client count"
                ])
            elif graph_type == "bw":
                args.extend([
                    "DEF:read_bytes=%s:read_bytes:AVERAGE" % rrd,
                    "DEF:write_bytes=%s:write_bytes:AVERAGE" % rrd,
                    "LINE2:read_bytes#ff0000:read bytes/sec",
                    "LINE2:write_bytes#0000ff:write bytes/sec"
                ])
            else:
                raise NotImplementedError
    elif subdir == "server":
        if graph_type == "cpumem":
            args.extend([
                        "DEF:pct_cpu=%s:pct_cpu:AVERAGE" % rrd,
                        "DEF:pct_mem=%s:pct_mem:AVERAGE" % rrd,
                        "LINE2:pct_cpu#ff0000:% cpu used",
                        "LINE2:pct_mem#0000ff:% ram used"
            ])
        else:
            raise NotImplementedError

    if size == ":small":
        args.extend([
                    "--width", "75", "--height", "100",
        ])
    elif size == ":tiny":
        args.extend([
                    "--only-graph", "--width", "100", "--height", "36",
        ])
    elif size == ":micro":
        args.extend([
                    "--only-graph", "--width", "50", "--height", "15",
        ])

    r, w = os.pipe()
    fcntl.fcntl(r, fcntl.F_SETFL, os.O_NONBLOCK)
    so = os.dup(sys.__stdout__.fileno())
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
            time.sleep(0.1)
            continue

    os.dup2(so, 1)
    os.close(r)
    os.close(w)
    os.close(so)
    return image_data.getvalue(), "image/%s" % image_type
