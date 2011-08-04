#!/usr/bin/env python
from django.core.management import setup_environ
import settings
setup_environ(settings)

from monitor.models import *
from configure.models import *

from collections_24 import defaultdict
import sys

from logging import getLogger, FileHandler, INFO, StreamHandler
file_log_name = __name__
getLogger(file_log_name).setLevel(INFO)
getLogger(file_log_name).addHandler(FileHandler("%s.log" % 'hydra'))

def log():
    return getLogger(file_log_name)

def screen(string):
    print string 
    log().debug(string)


import cmd
from texttable import Texttable

class HydraDebug(cmd.Cmd, object):
    def __init__(self):
        super(HydraDebug, self).__init__()
        self.prompt = "Hydra> "

    def precmd(self, line):
        log().debug("> %s" % line)
        return line

    def do_EOF(self, line):
        raise KeyboardInterrupt()

    def _create_target_mounts(self, node, target, failover_host):
        ManagedTargetMount.objects.get_or_create(
            block_device = node,
            target = target,
            host = node.host, 
            mount_point = target.default_mount_path(node.host),
            primary = True)

        if failover_host:
            # NB have to do this the long way because get_or_create will do the wrong thing on block_device=None 
            try:
                tm = ManagedTargetMount.objects.get(
                    target = target,
                    host = failover_host, 
                    mount_point = target.default_mount_path(failover_host),
                    primary = False)
            except ManagedTargetMount.DoesNotExist:
                tm = ManagedTargetMount(
                    block_device = None,
                    target = target,
                    host = failover_host, 
                    mount_point = target.default_mount_path(failover_host),
                    primary = False)
                tm.save()

    def _load_target_config(self, info):
        host = Host.objects.get(address = info['host'])
        try:
            failover_host = Host.objects.get(address = info['failover_host'])
        except KeyError:
            failover_host = None
        node, created = LunNode.objects.get_or_create(host = host, path = info['device_node'])

        return node, host, failover_host

    def do_load_config(self, config_file):
        import json
        text = open(config_file).read()
        data = json.loads(text)

        # FIXME: we rely on the good faith of the .json file's author to use
        # our canonical names for devices.  We must normalize them to avoid
        # the risk of double-using a LUN.

        for host_info in data['hosts']:
            host = ManagedHost.objects.get_or_create(address = host_info['address'])
            host, ssh_monitor = SshMonitor.from_string(host_info['address'])
            host.save()
            ssh_monitor.host = host
            ssh_monitor.save()

        for mgs_info in data['mgss']:
            node, host, failover_host = self._load_target_config(mgs_info)

            try:
                mgs = ManagedMgs.objects.get(targetmount__host = host)
            except ManagedMgs.DoesNotExist:
                mgs = ManagedMgs(name = "MGS")
                mgs.save()

            self._create_target_mounts(node, mgs, failover_host)

        for filesystem_info in data['filesystems']:
            fs_mgs_host = Host.objects.get(address = filesystem_info['mgs'])
            mgs = ManagedMgs.objects.get(targetmount__host = fs_mgs_host)
            filesystem, created = Filesystem.objects.get_or_create(name = filesystem_info['name'], mgs = mgs)

            mds_info = filesystem_info['mds']
            mdt_node, mdt_host, mdt_failover_host = self._load_target_config(mds_info)
            try:
                mdt = ManagedMdt.objects.get(targetmount__block_device = mdt_node)
            except ManagedMdt.DoesNotExist:
                mdt = ManagedMdt(filesystem = filesystem)
                mdt.save()

            self._create_target_mounts(mdt_node, mdt, mdt_failover_host)

            for oss_info in filesystem_info['osss']:
                for device_node in oss_info['device_nodes']:
                    tmp_oss_info = oss_info
                    oss_info['device_node'] = device_node
                    node, host, failover_host = self._load_target_config(tmp_oss_info)

                    try:
                        oss = ManagedOst.objects.get(targetmount__block_device = node)
                    except ManagedOst.DoesNotExist:
                        oss = ManagedOst(filesystem = filesystem)
                        oss.save()

                        self._create_target_mounts(node, oss, failover_host)

    def do_format_fs(self, args):
        from configure.models import FormatTargetJob
        fs = Filesystem.objects.all()[0]
        for target in fs.get_targets():
            if target.state == 'unformatted':
                FormatTargetJob(target = target).run()

    def do_start(self, fs_name):
        from configure.models import StartTargetMountJob
        fs = Filesystem.objects.get(name = fs_name)
        for target in fs.get_targets():
            tm = target.targetmount_set.get(primary = True).downcast()
            if tm.state == 'unmounted':
                StartTargetMountJob(target_mount = tm).run()

    def do_stop(self, fs_name):
        from configure.models import StopTargetMountJob
        fs = Filesystem.objects.get(name = fs_name)
        for target in fs.get_targets():
            tm = target.targetmount_set.get(primary = True).downcast()
            if tm.state == 'mounted':
                StopTargetMountJob(target_mount = tm).run()

    def do_transition(self, args):
        from configure.lib.state_manager import StateManager
        s = StateManager()

        #s.set_state(ManagedMdt.objects.get(), 'registered')
        s.set_state(ManagedMdt.objects.get().targetmount_set.get(primary=True).downcast(), 'mounted')

    def do_lnet_up(self, args):
        from configure.models import LoadLNetJob
        from configure.models import StartLNetJob
        for host in ManagedHost.objects.all():
            LoadLNetJob(host = host).run()
            StartLNetJob(host = host).run()

    def do_lnet_down(self, args):
        from configure.models import StopLNetJob
        from configure.models import UnloadLNetJob
        for host in ManagedHost.objects.all():
            StopLNetJob(host = host).run()
            UnloadLNetJob(host = host).run()

if __name__ == '__main__':
    cmdline = HydraDebug

    if len(sys.argv) == 1:
        try:
            cmdline().cmdloop()
        except KeyboardInterrupt:
            screen("Exiting...")
    else:
        cmdline().onecmd(" ".join(sys.argv[1:]))

