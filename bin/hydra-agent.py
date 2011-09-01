#!/usr/bin/env python
#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

import hydra_agent.actions as actions
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'Hydra Agent.')
    subparsers = parser.add_subparsers()

    parser_register_target = subparsers.add_parser('register-target',
                                                   help='register a target')
    parser_register_target.add_argument('--device', required=True,
                                        help='device for target')
    parser_register_target.add_argument('--mountpoint', required=True,
                                         help='mountpoint for target')
    parser_register_target.set_defaults(func=actions.register_target)

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
    parser_configure_ha.set_defaults(func=actions.configure_ha)

    parser_mount_target = subparsers.add_parser('mount-target',
                                                help='mount a target')
    parser_mount_target.add_argument('--label', required=True,
                                     help='label of target to mount')
    parser_mount_target.set_defaults(func=actions.mount_target)

    parser_unmount_target = subparsers.add_parser('unmount-target',
                                                  help='unmount a target')
    parser_unmount_target.add_argument('--label', required=True,
                                       help='label of target to unmount')
    parser_unmount_target.set_defaults(func=actions.unmount_target)

    parser_start_target = subparsers.add_parser('start-target',
                                                help='start a target')
    parser_start_target.add_argument('--label', required=True,
                                       help='label of target to start')
    parser_start_target.set_defaults(func=actions.start_target)

    parser_stop_target = subparsers.add_parser('stop-target',
                                                help='stop a target')
    parser_stop_target.add_argument('--label', required=True,
                                    help='label of target to stop')
    parser_stop_target.set_defaults(func=actions.stop_target)

    parser_format_target = subparsers.add_parser('format-target',
                                                 help='format a target')
    parser_format_target.add_argument('--args', required=True,
                                      help='format arguments')
    parser_format_target.set_defaults(func=actions.format_target)

    parser_locate_device = subparsers.add_parser('locate-device',
                        help='find a device node path from a filesystem UUID')
    parser_locate_device.add_argument('--uuid', required=True,
                                      help='label of target to find')
    parser_locate_device.set_defaults(func=actions.locate_device)

    parser_audit = subparsers.add_parser('audit', help='report lustre status')
    parser_audit.set_defaults(func=actions.audit)

    args = parser.parse_args()
    args.func(args)
