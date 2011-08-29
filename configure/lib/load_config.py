
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from configure.models import *
from monitor.models import LunNode

def _create_target_mounts(node, target, failover_host):
    ManagedTargetMount.objects.get_or_create(
        block_device = node,
        target = target,
        host = node.host, 
        mount_point = target.default_mount_path(node.host),
        primary = True)

    if failover_host:
        if node.lun:
            try:
                failover_node = LunNode.objects.get(host = failover_host, lun = node.lun)
            except LunNode.DoesNotExist:
                failover_node = None
        else:
            failover_node = None
        # NB have to do this the long way because get_or_create will do the wrong thing on block_device=None 
        try:
            tm = ManagedTargetMount.objects.get(
                target = target,
                host = failover_host, 
                mount_point = target.default_mount_path(failover_host),
                primary = False)
        except ManagedTargetMount.DoesNotExist:
            tm = ManagedTargetMount(
                block_device = failover_node,
                target = target,
                host = failover_host, 
                mount_point = target.default_mount_path(failover_host),
                primary = False)
            tm.save()

def _load_target_config(info):
    host = ManagedHost.objects.get(address = info['host'])
    try:
        failover_host = ManagedHost.objects.get(address = info['failover_host'])
    except KeyError:
        failover_host = None
    node, created = LunNode.objects.get_or_create(host = host, path = info['device_node'])

    return node, host, failover_host

# FIXME: we rely on the good faith of the .json file's author to use
# our canonical names for devices.  We must normalize them to avoid
# the risk of double-using a LUN.
def _load(text):
    import json
    data = json.loads(text)


    for host_info in data['hosts']:
        host, created = ManagedHost.objects.get_or_create(address = host_info['address'])
        if created:
            host, ssh_monitor = SshMonitor.from_string(host_info['address'])
            host.save()
            ssh_monitor.host = host
            ssh_monitor.save()

    for mgs_info in data['mgss']:
        node, host, failover_host = _load_target_config(mgs_info)

        try:
            mgs = ManagedMgs.objects.get(targetmount__host = host)
        except ManagedMgs.DoesNotExist:
            mgs = ManagedMgs(name = "MGS")
            mgs.save()

        _create_target_mounts(node, mgs, failover_host)

    for filesystem_info in data['filesystems']:
        fs_mgs_host = ManagedHost.objects.get(address = filesystem_info['mgs'])
        mgs = ManagedMgs.objects.get(targetmount__host = fs_mgs_host)
        filesystem, created = ManagedFilesystem.objects.get_or_create(name = filesystem_info['name'], mgs = mgs)

        mds_info = filesystem_info['mds']
        mdt_node, mdt_host, mdt_failover_host = _load_target_config(mds_info)
        try:
            mdt = ManagedMdt.objects.get(targetmount__block_device = mdt_node)
        except ManagedMdt.DoesNotExist:
            mdt = ManagedMdt(filesystem = filesystem)
            mdt.save()

        _create_target_mounts(mdt_node, mdt, mdt_failover_host)

        for oss_info in filesystem_info['osss']:
            for device_node in oss_info['device_nodes']:
                tmp_oss_info = oss_info
                oss_info['device_node'] = device_node
                node, host, failover_host = _load_target_config(tmp_oss_info)

                try:
                    oss = ManagedOst.objects.get(targetmount__block_device = node)
                except ManagedOst.DoesNotExist:
                    oss = ManagedOst(filesystem = filesystem)
                    oss.save()

                    _create_target_mounts(node, oss, failover_host)

from django.db import transaction
@transaction.commit_on_success
def load_string(text):
    _load(text)

from django.db import transaction
@transaction.commit_on_success
def load_file(path):
    text = open(path).read()
    _load(text)
