#!/usr/bin/env python
#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

import hydra_agent.actions as actions
from hydra_agent.store import store_init

import pickle
import simplejson as json
import argparse

if __name__ == '__main__':
    store_init()

    parser = argparse.ArgumentParser(description = 'Hydra Agent.')
    subparsers = parser.add_subparsers()

    p = subparsers.add_parser('register-target', help='register a target')
    p.add_argument('--device', required=True, help='device for target')
    p.add_argument('--mountpoint', required=True, help='mountpoint for target')
    p.set_defaults(func=actions.register_target)

    p = subparsers.add_parser('configure-ha',
                              help='configure a target\'s HA parameters')
    p.add_argument('--device', required=True, help='device of the target')
    p.add_argument('--label', required=True, help='label of the target')
    p.add_argument('--uuid', required=True, help='uuid of the target')
    p.add_argument('--serial', required=True, help='serial of the target')
    p.add_argument('--primary', action='store_true',
                   help='target is primary on this node')
    p.add_argument('--mountpoint', required=True, help='mountpoint for target')
    p.set_defaults(func=actions.configure_ha)

    p = subparsers.add_parser('unconfigure-ha',
                              help='unconfigure a target\'s HA parameters')
    p.add_argument('--label', required=True, help='label of the target')
    p.add_argument('--uuid', required=True, help='uuid of the target')
    p.add_argument('--serial', required=True, help='serial of target')
    p.add_argument('--primary', action='store_true',
                   help='target is primary on this node')
    p.set_defaults(func=actions.unconfigure_ha)

    p = subparsers.add_parser('mount-target', help='mount a target')
    p.add_argument('--uuid', required=True, help='uuid of target to mount')
    p.set_defaults(func=actions.mount_target)

    p = subparsers.add_parser('unmount-target', help='unmount a target')
    p.add_argument('--uuid', required=True, help='uuid of target to unmount')
    p.set_defaults(func=actions.unmount_target)

    p = subparsers.add_parser('start-target', help='start a target')
    p.add_argument('--label', required=True, help='label of target to start')
    p.add_argument('--serial', required=True, help='serial of target to start')
    p.set_defaults(func=actions.start_target)

    p = subparsers.add_parser('stop-target', help='stop a target')
    p.add_argument('--label', required=True, help='label of target to stop')
    p.add_argument('--serial', required=True, help='serial of target to stop')
    p.set_defaults(func=actions.stop_target)

    p = subparsers.add_parser('format-target', help='format a target')
    p.add_argument('--args', required=True, help='format arguments')
    p.set_defaults(func=actions.format_target)

    p = subparsers.add_parser('migrate-target',
                              help='migrate a target to a node')
    p.add_argument('--label', required=True, help='label of target to migrate')
    p.add_argument('--node', required=True, help='node to migrate target to')
    p.set_defaults(func=actions.migrate_target)

    p = subparsers.add_parser('unmigrate-target',
                              help='cancel prevous target migrate')
    p.add_argument('--label', required=True,
                   help='label of target to cancel migration of')
    p.set_defaults(func=actions.unmigrate_target)

    p = subparsers.add_parser('target-running',
                              help='check if a target is running')
    p.add_argument('--uuid', required=True,
                   help='uuid of target to check')
    p.set_defaults(func=actions.target_running)

    p = subparsers.add_parser('fail-node',
                              help='fail (i.e. shut down) this node')
    p.set_defaults(func=actions.fail_node)

    p = subparsers.add_parser('configure-rsyslog',
                          help='configure rsyslog to forward to another node')
    p.add_argument('--node', required=True, help='node to direct syslog to')
    p.set_defaults(func=actions.configure_rsyslog)

    p = subparsers.add_parser('unconfigure-rsyslog',
                        help='unconfigure rsyslog to forward to another node')
    p.set_defaults(func=actions.unconfigure_rsyslog)

    p = subparsers.add_parser('get-fqdn')
    p.set_defaults(func=actions.get_fqdn)
    p = subparsers.add_parser('update-scan')
    p.set_defaults(func=actions.update_scan)
    p = subparsers.add_parser('detect-scan')
    p.set_defaults(func=actions.detect_scan)
    p = subparsers.add_parser('lnet-scan')
    p.set_defaults(func=actions.lnet_scan)
    p = subparsers.add_parser('device-scan')
    p.set_defaults(func=actions.device_scan)
    p = subparsers.add_parser('set-conf-param')
    p.add_argument('--args', required=True)
    p.set_defaults(func=actions.set_conf_param)
    p = subparsers.add_parser('stop-lnet')
    p.set_defaults(func=actions.stop_lnet)
    p = subparsers.add_parser('start-lnet')
    p.set_defaults(func=actions.start_lnet)
    p = subparsers.add_parser('load-lnet')
    p.set_defaults(func=actions.load_lnet)
    p = subparsers.add_parser('unload-lnet')
    p.set_defaults(func=actions.unload_lnet)
    p = subparsers.add_parser('clear-targets')
    p.set_defaults(func=actions.clear_targets)

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


