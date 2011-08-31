#!/usr/bin/env python
#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from hydra_agent.audit import LocalLustreAudit

import argparse
import sys
import os
import tempfile
import simplejson as json
import time

LIBDIR = "/var/lib/hydra"

if __name__ == '__main__':
    def create_libdir():
        try:
            os.makedirs(LIBDIR)
        except:
            pass

    parser = argparse.ArgumentParser(description = 'Hydra Agent.')
    parser.add_argument('--register_target', nargs = 2,
                        help='register a target')
    parser.add_argument('--configure_ha', nargs = 4,
                        help='configure a target\'s HA parameters')
    parser.add_argument('--mount_target', nargs = 1, help='mount a target')
    parser.add_argument('--unmount_target', nargs = 1, help='unmount a target')
    parser.add_argument('--start_target', nargs = 1, help='start a target')
    parser.add_argument('--stop_target', nargs = 1, help='stop a target')
    parser.add_argument('--format_target', nargs = 1, help='format a target')
    parser.add_argument('--locate_device', nargs = 1, help='find a device node path from a filesystem UUID')

    args = parser.parse_args()
    
    if args.locate_device != None:
        uuid = args.locate_device[0]
        lla = LocalLustreAudit()
        lla.read_mounts()
        lla.read_fstab()
        device_nodes = lla.get_device_nodes()
        node_result = None
        for d in device_nodes:
            if d['fs_uuid'] == uuid:
                node_result = d
        print json.dumps(node_result) 
        sys.exit(0)

    if args.format_target != None:
        from hydra_agent.cmds import lustre
        import shlex, subprocess

        kwargs = json.loads(args.format_target[0])
        cmdline = lustre.mkfs(**kwargs)

        rc = subprocess.call(shlex.split(cmdline), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if rc != 0:
            sys.exit(rc)

        p = subprocess.Popen(["blkid", "-o", "value", "-s", "UUID", kwargs['device']], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        stdout, stderr = p.communicate()
        rc = p.wait()
        if rc != 0:
            sys.exit(rc)

        uuid = stdout.strip()

        print json.dumps({'uuid': uuid})
        sys.exit(0)

    if args.register_target != None:
        bdev = args.register_target[0]
        mntpt = args.register_target[1]

        create_libdir()

        try:
            os.makedirs(mntpt)
        except:
            pass

        os.system("mount -t lustre %s %s" % (bdev, mntpt))
        # XXX - wait for the monitor to catch up
        #       should be removed when we can pass the name back to the server
        time.sleep(10)
        os.system("umount %s" % mntpt)

        # get the label to pass back to the server
        label = os.popen("blkid -o value -s LABEL %s" % bdev).readline().rstrip()

        print json.dumps({'label': label})
        sys.exit(0)

    if args.configure_ha != None:
        bdev = args.configure_ha[0]
        label = args.configure_ha[1]
        primary = args.configure_ha[2]
        mntpt = args.configure_ha[3]

        if primary == "True":
            # now configure pacemaker for this target
            # XXX - crm is a python script -- should look into interfacing
            #       with it directly
            os.system("crm configure primitive %s ocf:hydra:Target meta target-role=\"stopped\" operations \$id=\"%s-operations\" op monitor interval=\"120\" timeout=\"60\" op start interval=\"0\" timeout=\"300\" op stop interval=\"0\" timeout=\"300\" params target=\"%s\"" % (label, label, label))

        create_libdir()

        try:
            os.makedirs(mntpt)
        except:
            pass

        # save the metadata for the mount
        file = open("%s/%s" % (LIBDIR, label), 'w')
        json.dump({"bdev": bdev, "mntpt": mntpt}, file)
        file.close()

        sys.exit(0)

    if args.mount_target != None:
        label = args.mount_target[0]

        file = open("%s/%s" % (LIBDIR, label), 'r')
        j = json.load(file)
        file.close()
 
        os.system("mount -t lustre %s %s" % (j['bdev'], j['mntpt']))

        sys.exit(0)

    if args.unmount_target != None:
        label = args.unmount_target[0]

        file = open("%s/%s" % (LIBDIR, label), 'r')
        j = json.load(file)
        file.close()
 
        os.system("umount %s" % j['bdev'])

        sys.exit(0)

    if args.start_target != None:
        label = args.start_target[0]

        os.system("crm resource start %s" % label)

        sys.exit(0)

    if args.stop_target != None:
        label = args.stop_target[0]

        os.system("crm resource stop %s" % label)

        sys.exit(0)

    print LocalLustreAudit().audit_info()

