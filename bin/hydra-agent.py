#!/usr/bin/env python
#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from hydra_agent.audit import LocalLustreAudit

import argparse
import sys
import errno
import os
import shlex, subprocess
import tempfile
import simplejson as json

LIBDIR = "/var/lib/hydra"

if __name__ == '__main__':
    def create_libdir():
        try:
            os.makedirs(LIBDIR)
        except OSError, e:
            if e.errno == errno.EEXIST:
                pass
            else:
                print >>sys.stderr, "failed to create LIBDIR: ", e
                sys.exit(-1)

    def locate_device(args):
        lla = LocalLustreAudit()
        lla.read_mounts()
        lla.read_fstab()
        device_nodes = lla.get_device_nodes()
        node_result = None
        for d in device_nodes:
            if d['fs_uuid'] == args.uuid:
                node_result = d
        print json.dumps(node_result) 
        sys.exit(0)

    def format_target(args):
        from hydra_agent.cmds import lustre
        import shlex, subprocess

        kwargs = json.loads(args.args)
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

    def register_target(args):
        create_libdir()

        try:
            os.makedirs(args.mountpoint)
        except OSError, e:
            if e.errno == errno.EEXIST:
                pass
            else:
                print >>sys.stderr, "failed to create mount point: ", e
                sys.exit(-1)

        try:
            rc = subprocess.call(shlex.split("mount -t lustre %s %s" % \
                                             (args.device, args.mountpoint)),
                                 stdout=open(os.devnull, "w"))
            if rc < 0:
                print >>sys.stderr, "mount failed: ", rc
        except OSError, e:
            print >>sys.stderr, "failed to execute subprocess: ", e
            rc = -1

        if rc < 0:
            sys.exit(rc)

        try:
            rc = subprocess.call(shlex.split("umount %s" % args.mountpoint),
                                 stdout=open(os.devnull, "w"))
            if rc < 0:
                print >>sys.stderr, "unmount failed: ", rc
        except OSError, e:
            print >>sys.stderr, "failed to execute subprocess: ", e
            rc = -1

        if rc < 0:
            sys.exit(rc)

        # get the label to pass back to the server
        try:
            proc = subprocess.Popen("blkid -o value -s LABEL %s" % args.device,
                                     shell=True, stdout=subprocess.PIPE)
            label = proc.communicate()[0].rstrip()
            rc = proc.wait()
            if rc < 0:
                print >>sys.stderr, "blkid failed: ", rc
        except OSError, e:
            print >>sys.stderr, "failed to execute subprocess: ", e
            rc = -1

        if rc < 0:
            sys.exit(rc)

        print json.dumps({'label': label})
        sys.exit(0)

    def configure_ha(args):
        if args.primary:
            # now configure pacemaker for this target
            # XXX - crm is a python script -- should look into interfacing
            #       with it directly
            try:
                rc = subprocess.call(shlex.split("crm configure primitive %s ocf:hydra:Target meta target-role=\"stopped\" operations \$id=\"%s-operations\" op monitor interval=\"120\" timeout=\"60\" op start interval=\"0\" timeout=\"300\" op stop interval=\"0\" timeout=\"300\" params target=\"%s\"" % (args.label, args.label, args.label)),
                                     stdout=open(os.devnull, "w"))
                if rc < 0:
                    print >>sys.stderr, "crm configure primative failed: ", rc
            except OSError, e:
                print >>sys.stderr, "failed to execute subprocess: ", e
                rc = -1
            if rc < 0:
                sys.exit(rc)

        create_libdir()

        try:
            os.makedirs(args.mountpoint)
        except OSError, e:
            if e.errno == errno.EEXIST:
                pass
            else:
                print >>sys.stderr, "failed to create mount point: ", e
                sys.exit(-1)

        # save the metadata for the mount
        try:
            file = open("%s/%s" % (LIBDIR, args.label), 'w')
            json.dump({"bdev": args.device, "mntpt": args.mountpoint}, file)
            file.close()
        except IOError, e:
            print >>sys.stderr, "failed to write target data: ", e
            sys.exit(-1)
        sys.exit(0)

    def mount_target(args):
        try:
            file = open("%s/%s" % (LIBDIR, args.label), 'r')
            j = json.load(file)
            file.close()
        except IOError, e:
            print >>sys.stderr, "failed to read target data: ", e
            sys.exit(-1)
 
        try:
            rc = subprocess.call(shlex.split("mount -t lustre %s %s" % \
                                             (j['bdev'], j['mntpt'])),
                                 stdout=open(os.devnull, "w"))
            if rc < 0:
                print >>sys.stderr, "crm resource start failed: ", rc
        except OSError, e:
            print >>sys.stderr, "failed to execute subprocess: ", e
            rc = -1
        sys.exit(rc)

    def unmount_target(args):
        try:
            file = open("%s/%s" % (LIBDIR, args.label), 'r')
            j = json.load(file)
            file.close()
        except IOError, e:
            print >>sys.stderr, "failed to read target data: ", e
            sys.exit(-1)
 
        try:
            rc = subprocess.call(shlex.split("umount %s" % j['bdev']),
                                 stdout=open(os.devnull, "w"))
            if rc < 0:
                print >>sys.stderr, "umount failed: ", rc
        except OSError, e:
            print >>sys.stderr, "failed to execute subprocess: ", e
            rc = -1
        sys.exit(rc)

    def start_target(args):
        try:
            rc = subprocess.call(shlex.split("crm resource start %s" % \
                                             args.label),
                                 stdout=open(os.devnull, "w"))
            if rc < 0:
                print >>sys.stderr, "crm resource start failed: ", rc
        except OSError, e:
            print >>sys.stderr, "failed to execute subprocess: ", e
            rc = -1
        sys.exit(rc)

    def stop_target(args):
        try:
            rc = subprocess.call(shlex.split("crm resource stop %s" % \
                                             args.label),
                                 stdout=open(os.devnull, "w"))
            if rc < 0:
                print >>sys.stderr, "crm resource stop failed: ", rc
        except OSError, e:
            print >>sys.stderr, "failed to execute subprocess: ", e
            rc = -1
        sys.exit(rc)

    def audit(args):
        print LocalLustreAudit().audit_info()

    parser = argparse.ArgumentParser(description = 'Hydra Agent.')
    subparsers = parser.add_subparsers()

    parser_register_target = subparsers.add_parser('register-target',
                                                   help='register a target')
    parser_register_target.add_argument('--device', required=True,
                                        help='device for target')
    parser_register_target.add_argument('--mountpoint', required=True,
                                         help='mountpoint for target')
    parser_register_target.set_defaults(func=register_target)

    parser_configure_ha = subparsers.add_parser('configure-ha',
                                 help='configure a target\'s HA parameters')
    parser_configure_ha.add_argument('--device', required=True,
                                     help='device for target')
    parser_configure_ha.add_argument('--label', required=True,
                                     help='label for target')
    parser_configure_ha.add_argument('--primary', action='store_true',
                                     help='target is primary on this node')
    parser_configure_ha.add_argument('--mountpoint', required=True,
                                     help='mountpoint for target')
    parser_configure_ha.set_defaults(func=configure_ha)

    parser_mount_target = subparsers.add_parser('mount-target',
                                                help='mount a target')
    parser_mount_target.add_argument('--label', required=True,
                                     help='label of target to mount')
    parser_mount_target.set_defaults(func=mount_target)

    parser_unmount_target = subparsers.add_parser('unmount-target',
                                                  help='unmount a target')
    parser_unmount_target.add_argument('--label', required=True,
                                       help='label of target to unmount')
    parser_unmount_target.set_defaults(func=unmount_target)

    parser_start_target = subparsers.add_parser('start-target',
                                                help='start a target')
    parser_start_target.add_argument('--label', required=True,
                                       help='label of target to start')
    parser_start_target.set_defaults(func=start_target)

    parser_stop_target = subparsers.add_parser('stop-target',
                                                help='stop a target')
    parser_stop_target.add_argument('--label', required=True,
                                    help='label of target to stop')
    parser_stop_target.set_defaults(func=stop_target)

    parser_format_target = subparsers.add_parser('format-target',
                                                 help='format a target')
    parser_format_target.add_argument('--args', required=True,
                                      help='format arguments')
    parser_format_target.set_defaults(func=format_target)

    parser_locate_device = subparsers.add_parser('locate-device',
                        help='find a device node path from a filesystem UUID')
    parser_locate_device.add_argument('--uuid', required=True,
                                      help='label of target to find')
    parser_locate_device.set_defaults(func=locate_device)

    parser_audit = subparsers.add_parser('audit', help='report lustre status')
    parser_audit.set_defaults(func=audit)

    args = parser.parse_args()
    args.func(args)
