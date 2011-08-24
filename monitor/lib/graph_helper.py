
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

import time
import re
import os, sys, fcntl
import rrdtool
from monitor.models import *
from cStringIO import StringIO

def load_graph(name):
    image_type = "png"
    graph_dir = "/var/lib/cerebro/graphs"
    graph_path = "%s/%s.%s" % (graph_dir, name, image_type)
    image_data = open(graph_path, "rb").read()
    return image_data, "image/%s" % image_type

def dyn_load_graph(subdir, name, graph_type, in_params):
    # TODO: Refactor the hell out of this stuff.  Maybe switch to OO-style
    # organization?
    image_type = "png"
    rrd_home = "/var/lib/cerebro/rrds"
    rrd = "%s/%s.rrd" % (rrd_home, name)
    params = in_params.copy()
    # TODO: properly handle required params
    if not params.has_key("size"):
        params["size"] = "normal" 
    if not params.has_key("start"):
        params["start"] = "%d" % (time.time() - 600)

    args = [
        "-",
        "--start", "%s" % params["start"],
    ]
    if subdir == "aggregate":
        fs = Filesystem.objects.get(name=re.sub('aggregate/', '', name))
        osts = []
        mdts = []
        for target in fs.get_filesystem_targets():
            if re.search("OST", target.name):
                osts.append(target.name)
            else:
                mdts.append(target.name)

        if graph_type == "ost_space":
            if len(osts) < 2:
                newname = "target/%s" % osts[0]
                return dyn_load_graph("target", newname, "space", params)

            free_kb_cdef = "CDEF:agg_kb_free=%s_kb_free,%s_kb_free,+" % (osts[0], osts[1])
            used_kb_cdef = "CDEF:agg_kb_used=%s_kb_used,%s_kb_used,+" % (osts[0], osts[1])
            free_id_cdef = "CDEF:agg_id_free=%s_id_free,%s_id_free,+" % (osts[0], osts[1])
            used_id_cdef = "CDEF:agg_id_used=%s_id_used,%s_id_used,+" % (osts[0], osts[1])
            for i in range(len(osts)):
                args.extend([
                    "DEF:%s_kb_free=%s/target/%s.rrd:kbytes_free:AVERAGE" % (osts[i], rrd_home, osts[i]),
                    "DEF:%s_kb_used=%s/target/%s.rrd:kbytes_used:AVERAGE" % (osts[i], rrd_home, osts[i]),
                    "DEF:%s_id_free=%s/target/%s.rrd:inodes_free:AVERAGE" % (osts[i], rrd_home, osts[i]),
                    "DEF:%s_id_used=%s/target/%s.rrd:inodes_used:AVERAGE" % (osts[i], rrd_home, osts[i])
                ])
                if i > 1:
                    free_kb_cdef += ",%s_kb_free,+" % osts[i]
                    used_kb_cdef += ",%s_kb_used,+" % osts[i]
                    free_id_cdef += ",%s_id_free,+" % osts[i]
                    used_id_cdef += ",%s_id_used,+" % osts[i]
            free_kb_cdef += ",1024,*"
            used_kb_cdef += ",1024,*"
            args.extend([
                free_kb_cdef,
                used_kb_cdef,
                "CDEF:pct_kb_used=agg_kb_used,agg_kb_free,+,agg_kb_free,/,10,*",
                "LINE2:pct_kb_used#ff0000:% obj store used",
                "GPRINT:agg_kb_free:LAST:%.2lf%sB free",
                free_id_cdef,
                used_id_cdef,
                "CDEF:pct_id_used=agg_id_used,agg_id_free,+,agg_id_free,/,10,*",
                "LINE2:pct_id_used#0000ff:% obj inodes used",
                "GPRINT:agg_id_free:LAST:%.2lf%s inodes free",
            ])
        elif graph_type == "mdt_space":
            # just kick down to the individual target for now
            newname = "target/%s" % mdts[0]
            return dyn_load_graph("target", newname, "space", params)
        elif graph_type == "bw":
            if len(osts) < 2:
                newname = "target/%s" % osts[0]
                return dyn_load_graph("target", newname, graph_type, params)

            cdef_read = "CDEF:agg_read=%s_read_bytes,%s_read_bytes,+" % (osts[0], osts[1])
            cdef_write = "CDEF:agg_write=%s_write_bytes,%s_write_bytes,+" % (osts[0], osts[1])
            for i in range(len(osts)):
                args.extend([
                    "DEF:%s_read_bytes=%s/target/%s.rrd:read_bytes:AVERAGE" % (osts[i], rrd_home, osts[i]),
                    "DEF:%s_write_bytes=%s/target/%s.rrd:write_bytes:AVERAGE" % (osts[i], rrd_home, osts[i])
                ])
                if i > 1:
                    cdef_read += ",%s_read_bytes,+" % osts[i]
                    cdef_write += ",%s_write_bytes,+" % osts[i]
            args.extend([
                cdef_read,
                cdef_write,
                "LINE2:agg_read#ff0000:read bytes/sec",
                "GPRINT:agg_read:LAST:read %.2lf%sB/sec",
                "LINE2:agg_write#0000ff:write bytes/sec",
                "GPRINT:agg_write:LAST:write %.2lf%sB/sec",
                "PRINT:agg_read:LAST:read bw\:%.0lf",
                "PRINT:agg_write:LAST:write bw\:%.0lf",
            ])
        elif graph_type == "lock_rate":
            if len(osts) < 2:
                newname = "target/%s" % osts[0]
                return dyn_load_graph("target", newname, graph_type, params)

            cdef_grant_rate = "CDEF:agg_grant_rate=%s_grant_rate,%s_grant_rate,+" % (osts[0], osts[1])
            cdef_cancel_rate = "CDEF:agg_cancel_rate=%s_cancel_rate,%s_cancel_rate,+" % (osts[0], osts[1])
            for i in range(len(osts)):
                args.extend([
                    "DEF:%s_grant_rate=%s/target/%s.rrd:grant_rate:AVERAGE" % (osts[i], rrd_home, osts[i]),
                    "DEF:%s_cancel_rate=%s/target/%s.rrd:cancel_rate:AVERAGE" % (osts[i], rrd_home, osts[i])
                ])
                if i > 1:
                    cdef_grant_rate += ",%s_grant_rate,+" % osts[i]
                    cdef_cancel_rate += ",%s_cancel_rate,+" % osts[i]
            args.extend([
                cdef_grant_rate,
                cdef_cancel_rate,
                "LINE2:agg_grant_rate#ff0000:lock grants/sec",
                "GPRINT:agg_grant_rate:LAST:%.2lf%s grants/sec",
                "LINE2:agg_cancel_rate#0000ff:lock cancels/sec",
                "GPRINT:agg_cancel_rate:LAST:%.2lf%s cancels/sec",
            ])
        elif graph_type == "locks":
            if len(osts) < 2:
                newname = "target/%s" % osts[0]
                return dyn_load_graph("target", newname, graph_type, params)

            cdef_lock_count = "CDEF:agg_lock_count=%s_lock_count,%s_lock_count,+" % (osts[0], osts[1])
            for i in range(len(osts)):
                args.extend([
                    "DEF:%s_lock_count=%s/target/%s.rrd:lock_count:AVERAGE" % (osts[i], rrd_home, osts[i]),
                ])
                if i > 1:
                    cdef_lock_count += ",%s_lock_count,+" % osts[i]
            args.extend([
                cdef_lock_count,
                "LINE2:agg_lock_count#0000ff:locks",
                "GPRINT:agg_lock_count:LAST:%.0lf%s locks",
            ])
        elif graph_type == "iops":
            if len(osts) < 2:
                newname = "target/%s" % osts[0]
                return dyn_load_graph("target", newname, graph_type, params)

            cdef_iops = "CDEF:agg_iops=%s_iops,%s_iops,+" % (osts[0], osts[1])
            for i in range(len(osts)):
                args.extend([
                    "DEF:%s_iops=%s/target/%s.rrd:iops:AVERAGE" % (osts[i], rrd_home, osts[i]),
                ])
                if i > 1:
                    cdef_iops += ",%s_iops,+" % osts[i]
            args.extend([
                cdef_iops,
                "LINE2:agg_iops#ff0000:I/Os per RPC",
                "GPRINT:agg_iops:LAST:%.2lf%s I/Os per RPC",
            ])
        elif graph_type == "clients":
            if len(osts) < 2:
                newname = "target/%s" % osts[0]
                return dyn_load_graph("target", newname, "exports", params)

            cdef_num_clients = "CDEF:agg_num_clients=%s_num_exports,%s_num_exports,+" % (osts[0], osts[1])
            for i in range(len(osts)):
                args.extend([
                    "DEF:%s_num_exports=%s/target/%s.rrd:num_exports:AVERAGE" % (osts[i], rrd_home, osts[i]),
                ])
                if i > 1:
                    cdef_num_clients += ",%s_num_exports,+" % osts[i]
            # TODO: verify num_clients - 2 (MDS, MGS?)
            cdef_num_clients += ",%d,/,2,-" % len(osts)
            args.extend([
                cdef_num_clients,
                "LINE2:agg_num_clients#0000ff:clients",
                "GPRINT:agg_num_clients:LAST:%.0lf%s clients",
            ])
        else:
            # Assume this is an MDT stat and kick down to the single
            # MDT for now.
            newname = "target/%s" % mdts[0]
            return dyn_load_graph("target", newname, graph_type, params)

    if subdir == "target":
        if re.search("MDT", name):
            if graph_type == "space":
                args.extend([
                    "DEF:kbytes_free=%s:kbytes_free:AVERAGE" % rrd,
                    "DEF:kbytes_used=%s:kbytes_used:AVERAGE" % rrd,
                    "CDEF:pct_kb_used=kbytes_used,kbytes_free,+,kbytes_free,/",
                    "LINE2:pct_kb_used#ff0000:% md store used",
                    "CDEF:bytes_free=kbytes_free,1024,*",
                    "GPRINT:bytes_free:LAST:%.2lf%sB free",
                    "DEF:inodes_free=%s:inodes_free:AVERAGE" % rrd,
                    "DEF:inodes_used=%s:inodes_used:AVERAGE" % rrd,
                    "CDEF:pct_id_used=inodes_used,inodes_free,+,inodes_free,/",
                    "LINE2:pct_id_used#0000ff:% md inodes used",
                    "GPRINT:inodes_free:LAST:%.2lf%s inodes free",
                ])
            elif graph_type == "dirstats":
                args.extend([
                    "DEF:mkdir=%s:mkdir:AVERAGE" % rrd,
                    "DEF:rmdir=%s:rmdir:AVERAGE" % rrd,
                    "LINE2:mkdir#ff0000:mkdir/sec",
                    "GPRINT:mkdir:LAST:%.2lf%s mkdir/sec",
                    "LINE2:rmdir#0000ff:rmdir/sec",
                    "GPRINT:rmdir:LAST:%.2lf%s rmdir/sec",
                ])
            elif graph_type == "fhstats":
                args.extend([
                    "DEF:open=%s:open:AVERAGE" % rrd,
                    "DEF:close=%s:close:AVERAGE" % rrd,
                    "LINE2:open#ff0000:open/sec",
                    "GPRINT:open:LAST:%.2lf%s open/sec",
                    "LINE2:close#0000ff:close/sec",
                    "GPRINT:close:LAST:%.2lf%s close/sec",
                ])
            elif graph_type == "linkstats":
                args.extend([
                    "DEF:link=%s:link:AVERAGE" % rrd,
                    "DEF:unlink=%s:unlink:AVERAGE" % rrd,
                    "LINE2:link#ff0000:link/sec",
                    "GPRINT:link:LAST:%.2lf%s link/sec",
                    "LINE2:unlink#0000ff:unlink/sec",
                    "GPRINT:unlink:LAST:%.2lf%s unlink/sec",
                ])
            elif graph_type == "objstats":
                args.extend([
                    "DEF:create=%s:create:AVERAGE" % rrd,
                    "DEF:destroy=%s:destroy:AVERAGE" % rrd,
                    "LINE2:create#ff0000:create/sec",
                    "GPRINT:create:LAST:%.2lf%s create/sec",
                    "LINE2:destroy#0000ff:destroy/sec",
                    "GPRINT:destroy:LAST:%.2lf%s destroy/sec",
                ])
            elif graph_type == "attrstats":
                args.extend([
                    "DEF:setattr=%s:setattr:AVERAGE" % rrd,
                    "DEF:getattr=%s:getattr:AVERAGE" % rrd,
                    "LINE2:setattr#ff0000:setattr/sec",
                    "GPRINT:setattr:LAST:%.2lf%s setattr/sec",
                    "LINE2:getattr#0000ff:getattr/sec",
                    "GPRINT:getattr:LAST:%.2lf%s getattr/sec",
                ])
            elif graph_type == "statfs":
                args.extend([
                    "DEF:statfs=%s:statfs:AVERAGE" % rrd,
                    "LINE2:statfs#ff0000:statfs/sec",
                    "GPRINT:statfs:LAST:%.2lf%s statfs/sec",
                ])
            elif graph_type == "mknod":
                args.extend([
                    "DEF:mknod=%s:mknod:AVERAGE" % rrd,
                    "LINE2:mknod#ff0000:mknod/sec",
                    "GPRINT:mknod:LAST:%.2lf%s mknod/sec",
                ])
            elif graph_type == "rename":
                args.extend([
                    "DEF:rename=%s:rename:AVERAGE" % rrd,
                    "LINE2:rename#ff0000:rename/sec",
                    "GPRINT:rename:LAST:%.2lf%s rename/sec",
                ])
        else:
            if graph_type == "iops":
                args.extend([
                    "DEF:iops=%s:iops:AVERAGE" % rrd,
                    "LINE2:iops#ff0000:I/Os per RPC",
                    "GPRINT:iops:LAST:%.2lf I/Os per RPC"
                ])
            elif graph_type == "lock_rate":
                args.extend([
                    "DEF:grant_rate=%s:grant_rate:AVERAGE" % rrd,
                    "DEF:cancel_rate=%s:cancel_rate:AVERAGE" % rrd,
                    "LINE2:grant_rate#ff0000:lock grants/s",
                    "GPRINT:grant_rate:LAST:%.2lf grants/s",
                    "LINE2:cancel_rate#0000ff:lock cancels/s",
                    "GPRINT:cancel_rate:LAST:%.2lf cancels/s",
                ])
            elif graph_type == "locks":
                args.extend([
                    "DEF:lock_count=%s:lock_count:AVERAGE" % rrd,
                    "LINE2:lock_count#0000fb:locks",
                    "GPRINT:lock_count:LAST:%.0lf locks"
                ])
            elif graph_type == "exports":
                args.extend([
                    "DEF:num_exports=%s:num_exports:AVERAGE" % rrd,
                    "LINE2:num_exports#0000fb:exports",
                    "GPRINT:num_exports:LAST:%.0lf exports"
                ])
            elif graph_type == "bw":
                args.extend([
                    "DEF:read_bytes=%s:read_bytes:AVERAGE" % rrd,
                    "DEF:write_bytes=%s:write_bytes:AVERAGE" % rrd,
                    "LINE2:read_bytes#ff0000:read bytes/sec",
                    "GPRINT:read_bytes:LAST:read %.2lf%sB/sec",
                    "LINE2:write_bytes#0000ff:write bytes/sec",
                    "GPRINT:write_bytes:LAST:write %.2lf%sB/sec",
                ])
            elif graph_type == "space":
                args.extend([
                    "DEF:kbytes_free=%s:kbytes_free:AVERAGE" % rrd,
                    "DEF:kbytes_used=%s:kbytes_used:AVERAGE" % rrd,
                    "CDEF:pct_kb_used=kbytes_used,kbytes_free,+,kbytes_free,/",
                    "LINE2:pct_kb_used#ff0000:% obj store used",
                    "CDEF:bytes_free=kbytes_free,1024,*",
                    "GPRINT:bytes_free:LAST:%.2lf%sB free",
                    "DEF:inodes_free=%s:inodes_free:AVERAGE" % rrd,
                    "DEF:inodes_used=%s:inodes_used:AVERAGE" % rrd,
                    "CDEF:pct_id_used=inodes_used,inodes_free,+,inodes_free,/",
                    "LINE2:pct_id_used#0000ff:% obj inodes used",
                    "GPRINT:inodes_free:LAST:%.2lf%s inodes free",
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

    if params["size"] == "small":
        args.extend([
                    "--width", "75", "--height", "100",
        ])
    elif params["size"] == "tiny":
        args.extend([
                    "--only-graph", "--width", "100", "--height", "36",
        ])
    elif params["size"] == "micro":
        args.extend([
                    "--only-graph", "--width", "50", "--height", "15",
        ])
    else:
        args.extend([
                    "--width", "250",
        ])

    if params["size"] == "sparkline":
        args[0] = "/dev/null"
        image_data = rrdtool.graph([(a.encode('ascii')) for a in args])
        return dict(d.split(":") for d in image_data[2])
    else:
        image_data = rrdtool.graph2str([(a.encode('ascii')) for a in args])
        return image_data[3], "image/%s" % image_type

