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
        TargetMount.objects.get_or_create(
            block_device = node,
            target = target,
            host = node.host, 
            mount_point = target.default_mount_path(node.host),
            primary = True)

        if failover_host:
            # NB have to do this the long way because get_or_create will do the wrong thing on block_device=None 
            try:
                tm = TargetMount.objects.get(
                    target = target,
                    host = failover_host, 
                    mount_point = target.default_mount_path(failover_host),
                    primary = False)
            except TargetMount.DoesNotExist:
                tm = TargetMount(
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
            host = Host.objects.get_or_create(address = host_info['address'])
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

    def do_format(self, args):
        from configure.models import ManagedMgs
        from configure.tasks import FormatTargetJob
        target = ManagedMgs.objects.all()[0]
        print "do_format: %s" % target
        FormatTargetJob(target).run()

    def do_setup(self, args):
        from configure.tasks import SetupFilesystemJob
        fs = Filesystem.objects.all()[0]
        print "do_setup: %s" % fs
        SetupFilesystemJob(fs).run()

    def do_start(self, args):
        from configure.tasks import StartFilesystemJob
        fs = Filesystem.objects.all()[0]
        print "do_start: %s" % fs
        StartFilesystemJob(fs).run()

    def do_stop(self, args):
        from configure.tasks import StopFilesystemJob
        fs = Filesystem.objects.all()[0]
        print "do_stop: %s" % fs
        StopFilesystemJob(fs).run()



    def do_stop(self, args):
        from configure.tasks import StopFilesystemJob
        fs = Filesystem.objects.all()[0]
        print "do_stop: %s" % fs
        StopFilesystemJob(fs).run()



if __name__ == '__main__':
    cmdline = HydraDebug

    if len(sys.argv) == 1:
        try:
            cmdline().cmdloop()
        except KeyboardInterrupt:
            screen("Exiting...")
    else:
        cmdline().onecmd(" ".join(sys.argv[1:]))

