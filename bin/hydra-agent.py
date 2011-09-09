#!/usr/bin/env python
#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from hydra_agent.legacy_audit import LocalLustreAudit
import hydra_agent.actions as actions

import pickle
import simplejson as json
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


    parser_unconfigure_ha = subparsers.add_parser('unconfigure-ha',
                                 help='unconfigure a target\'s HA parameters')
    parser_unconfigure_ha.add_argument('--label', required=True,
                                     help='label for target')
    parser_unconfigure_ha.add_argument('--primary', action='store_true',
                                     help='target is primary on this node')
    parser_unconfigure_ha.set_defaults(func=actions.unconfigure_ha)


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

    parser_migrate_target = subparsers.add_parser('migrate-target',
                                            help='migrate a target to a node')
    parser_migrate_target.add_argument('--label', required=True,
                                        help='label of target to migrate')
    parser_migrate_target.add_argument('--node', required=True,
                                        help='node to migrate target to')
    parser_migrate_target.set_defaults(func=actions.migrate_target)

    parser_unmigrate_target = subparsers.add_parser('unmigrate-target',
                                         help='cancel prevous target migrate')
    parser_unmigrate_target.add_argument('--label', required=True,
                                help='label of target to cancel migration of')
    parser_unmigrate_target.set_defaults(func=actions.unmigrate_target)

    parser_fail_node = subparsers.add_parser('fail-node',
                                       help='fail (i.e. shut down) this node')
    parser_fail_node.set_defaults(func=actions.fail_node)

    parser_audit = subparsers.add_parser('audit', help='report lustre status')
    parser_audit.set_defaults(func=actions.audit)

    try:
        args = parser.parse_args()
        result = args.func(args)
        print json.dumps({'success': True, 'result': result}, indent = 2)
    except Exception, e:
        import sys
        import traceback
        exc_info = sys.exc_info()
        backtrace = '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))
        sys.stderr.write("%s\n" % backtrace)

        print json.dumps({'success': False, 'exception': pickle.dumps(e), 'backtrace': backtrace}, indent=2)
        # NB having caught the exception, we will finally return 0.  This is done in order to distinguish between internal errors in hydra-agent (nonzero return value) and exceptions while running command errors (zero return value, exception serialized and output)


