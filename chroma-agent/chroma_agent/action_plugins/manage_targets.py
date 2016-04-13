#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2015 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


import errno
import os
import re
import tempfile

from chroma_agent.chroma_common.lib import shell
from chroma_agent.chroma_common.filesystems.filesystem import FileSystem
from chroma_agent.chroma_common.blockdevices.blockdevice import BlockDevice
from chroma_agent.log import daemon_log, console_log
from chroma_agent import config
from chroma_agent.chroma_common.lib.exception_sandbox import exceptionSandBox


def writeconf_target(device=None, target_types=(), mgsnode=(), fsname=None,
                     failnode=(), servicenode=(), param={}, index=None,
                     comment=None, mountfsoptions=None, network=(),
                     erase_params=False, nomgs=False, writeconf=False,
                     dryrun=False, verbose=False, quiet=False):
    # freeze a view of the namespace before we start messing with it
    args = dict(locals())

    options = []

    # Workaround for tunefs.lustre being sensitive to argument order:
    # erase-params has to come first or it overrides preceding options.
    # (LU-1462)
    early_flag_options = {
        'erase_params': '--erase-params'
    }
    for arg, val in early_flag_options.items():
        if args[arg]:
            options.append("%s" % val)

    tuple_options = ["target_types", "mgsnode", "failnode", "servicenode", "network"]
    for name in tuple_options:
        arg = args[name]
        # ensure that our tuple arguments are always tuples, and not strings
        if not hasattr(arg, "__iter__"):
            arg = (arg,)

        if name == "target_types":
            for type in arg:
                options.append("--%s" % type)
        elif name == 'mgsnode':
            for mgs_nids in arg:
                options.append("--%s=%s" % (name, ",".join(mgs_nids)))
        else:
            if len(arg) > 0:
                options.append("--%s=%s" % (name, ",".join(arg)))

    dict_options = ["param"]
    for name in dict_options:
        arg = args[name]
        for key in arg:
            if arg[key] is not None:
                options.extend(["--%s" % name, "%s=%s" % (key, arg[key])])

    flag_options = {
        'nomgs': '--nomgs',
        'writeconf': '--writeconf',
        'dryrun': '--dryrun',
        'verbose': '--verbose',
        'quiet': '--quiet',
    }
    for arg in flag_options:
        if args[arg]:
            options.append("%s" % flag_options[arg])

    # everything else
    handled = set(flag_options.keys() + early_flag_options.keys() + tuple_options + dict_options)
    for name in set(args.keys()) - handled:
        if name == "device":
            continue
        value = args[name]

        if value is not None:
            options.append("--%s=%s" % (name, value))

    shell.try_run(['tunefs.lustre'] + options + [device])


def get_resource_location(resource_name):
    # FIXME: this may break on non-english systems or new versions of pacemaker
    rc, lines_text, stderr = shell.run(["crm_mon", "-1", "-r"])
    if rc != 0:
        # Pacemaker not running, or no resources configured yet
        return None

    before_resources = True
    for line in lines_text.split("\n"):
        # skip down to the resources part
        if before_resources:
            if line.startswith("Full list of resources:"):
                before_resources = False
            continue

        # only interested in Target resources
        if "(ocf::chroma:Target)" not in line:
            continue

        # The line can have 3 or 4 arguments so pad it out to at least 4 and
        # throw away any extra
        # credit it goes to Aric Coady for this little trick
        rsc_id, type, status, host = (line.rstrip().lstrip().split() + [None])[:4]

        # In later pacemakers a new entry is added for stopped servers
        # MGS_424f74   (ocf::chroma:Target):   (target-role:Stopped) Stopped
        # (target-role:Stopped) is new.
        if host == 'Stopped' and 'Stopped' in status:
            status = host
            host = None

        if rsc_id == resource_name:
            # host will be None if it's not started due to the trick above
            # because the host only shows up as the 4th item when it's
            # started and gets the padded value of None above when it's not
            return host

    return None


@exceptionSandBox(console_log, None)
def get_resource_locations():
    # FIXME: this may break on non-english systems or new versions of pacemaker
    """Parse `crm_mon -1` to identify where (if anywhere)
       resources (i.e. targets) are running."""

    rc, lines_text, stderr = shell.run(["crm_mon", "-1", "-r"])
    if rc != 0:
        # Pacemaker not running, or no resources configured yet
        return {"crm_mon_error": {"rc": rc,
                                  "stdout": lines_text,
                                  "stderr": stderr}}

    locations = {}
    before_resources = True
    for line in lines_text.split("\n"):
        # if we don't have a DC for this cluster yet, we can't really believe
        # anything it says
        if line == "Current DC: NONE":
            return {}

        # skip down to the resources part
        if before_resources:
            if line.startswith("Full list of resources:"):
                before_resources = False
            continue

        # only interested in Target resources
        if "(ocf::chroma:Target)" not in line:
            continue

        # The line can have 3 or 4 arguments so pad it out to at least 4 and
        # throw away any extra
        # credit it goes to Aric Coady for this little trick
        rsc_id, type, status, host = (line.lstrip().split() + [None])[:4]

        # In later pacemakers a new entry is added for stopped servers
        # MGS_424f74   (ocf::chroma:Target):   (target-role:Stopped) Stopped
        # (target-role:Stopped) is new.
        if host == 'Stopped' and 'Stopped' in status:
            status = host
            host = None

        locations[rsc_id] = host

    return locations


def check_block_device(device_type, path):
    """
    Precursor to formatting a device: check if there is already a filesystem on it.

    :param path: Path to a block device
    :param device_type: The type of device the path references
    :return The filesystem type of the filesystem on the device, or None if unoccupied.
    """
    return BlockDevice(device_type, path).filesystem_type


def format_target(device_type, target_name, device, backfstype,
                  target_types=(), mgsnode=(), fsname=None,
                  failnode=(), servicenode=(), param={}, index=None,
                  comment=None, mountfsoptions=None, network=(),
                  device_size=None, mkfsoptions=None,
                  reformat=False, stripe_count_hint=None, iam_dir=False,
                  dryrun=False, verbose=False, quiet=False):
    """Perform a mkfs.lustre operation on a target device.
       Device may be a number of devices, block"""

    # freeze a view of the namespace before we start messing with it
    args = dict(locals())
    options = []

    # Now remove the locals that are not parameters for mkfs.
    del args['device_type']
    del args['target_name']

    tuple_options = ["target_types", "mgsnode", "failnode", "servicenode", "network"]
    for name in tuple_options:
        arg = args[name]
        # ensure that our tuple arguments are always tuples, and not strings
        if not hasattr(arg, "__iter__"):
            arg = (arg,)

        if name == "target_types":
            for type in arg:
                options.append("--%s" % type)
        elif name == 'mgsnode':
            for mgs_nids in arg:
                options.append("--%s=%s" % (name, ",".join(mgs_nids)))
        else:
            if len(arg) > 0:
                options.append("--%s=%s" % (name, ",".join(arg)))

    flag_options = {
        'dryrun': '--dryrun',
        'reformat': '--reformat',
        'iam_dir': '--iam-dir',
        'verbose': '--verbose',
        'quiet': '--quiet',
    }

    for arg in flag_options:
        if args[arg]:
            options.append("%s" % flag_options[arg])

    dict_options = ["param"]
    for name in dict_options:
        for key, value in args[name].items():
            if value is not None:
                options.extend(["--%s" % name, "%s=%s" % (key, value)])

    # everything else
    handled = set(flag_options.keys() + tuple_options + dict_options)
    for name in set(args.keys()) - handled:
        if name == "device":
            continue
        value = args[name]
        if value is not None:
            options.append("--%s=%s" % (name, value))

    block_device = BlockDevice(device_type, device)
    filesystem = FileSystem(backfstype, device)

    filesystem.mkfs(target_name, options)

    return {'uuid': block_device.uuid,
            'filesystem_type': block_device.filesystem_type,
            'inode_size': filesystem.inode_size,
            'inode_count': filesystem.inode_count}


def _mkdir_p_concurrent(path):
    # To cope with concurrent calls with a common sub-path, we have to do
    # this in two steps:
    #  1. Create the common portion (e.g. /mnt/whamfs/)
    #  2. Create the unique portion (e.g. /mnt/whamfs/ost0/)
    # If we tried to do a single os.makedirs, we could get an EEXIST when
    # colliding on the creation of the common portion and therefore miss
    # creating the unique portion.

    path = path.rstrip("/")

    def mkdir_silent(path):
        try:
            os.makedirs(path)
        except OSError, e:
            if e.errno == errno.EEXIST:
                pass
            else:
                raise e

    parent = os.path.split(path)[0]
    mkdir_silent(parent)
    mkdir_silent(path)


def register_target(target_name, device_path, mount_point, backfstype):
    filesystem = FileSystem(backfstype, device_path)

    _mkdir_p_concurrent(mount_point)

    filesystem.mount(target_name, mount_point)

    filesystem.umount(target_name, mount_point)

    return {'label': filesystem.label}


def unconfigure_target_ha(primary, ha_label, uuid):
    from chroma_agent.lib.pacemaker import cibadmin

    if get_resource_location(ha_label):
        raise RuntimeError("cannot unconfigure-ha: %s is still running " %
                           ha_label)

    if primary:
        rc, stdout, stderr = cibadmin(["-D", "-X",
                                       "<rsc_location id=\"%s-primary\">" %
                                       ha_label])
        rc, stdout, stderr = cibadmin(["-D", "-X", "<primitive id=\"%s\">" %
                                       ha_label])

        if rc != 0 and rc != 234:
            raise RuntimeError("Error %s trying to cleanup resource %s" % (rc,
                               ha_label))

    else:
        rc, stdout, stderr = cibadmin(["-D", "-X",
                                       "<rsc_location id=\"%s-secondary\">" %
                                       ha_label])


def unconfigure_target_store(uuid):
    try:
        target = _get_target_config(uuid)
        os.rmdir(target['mntpt'])
    except KeyError:
        console_log.warn("Cannot retrieve target information")
    except IOError:
        console_log.warn("Cannot remove target mount folder: %s" % target['mntpt'])
    config.delete('targets', uuid)


def configure_target_store(device, uuid, mount_point, backfstype, target_name):
    # Logically this should be config.set - but an error condition exists where the configure_target_store
    # steps fail later on and so the config exists but the manager doesn't know. Meaning that a set fails
    # because of a duplicate, where as an update doesn't.
    # So use update because that updates or creates.
    config.update('targets', uuid, {'bdev': device,
                                    'mntpt': mount_point,
                                    'backfstype': backfstype,
                                    'target_name': target_name})


def configure_target_ha(primary, device, ha_label, uuid, mount_point):
    from chroma_agent.action_plugins.manage_corosync import cibadmin

    if primary:
        # If the target already exists with the same params, skip.
        # If it already exists with different params, that is an error
        rc, stdout, stderr = shell.run(["crm_resource", "-r", ha_label, "-g", "target"])
        if rc == 0:
            info = _get_target_config(stdout.rstrip("\n"))
            if info['bdev'] == device and info['mntpt'] == mount_point:
                return
            else:
                raise RuntimeError("A resource with the name %s already exists" % ha_label)

        tmp_f, tmp_name = tempfile.mkstemp()
        os.write(tmp_f, "<primitive class=\"ocf\" provider=\"chroma\" type=\"Target\" id=\"%s\">\
  <meta_attributes id=\"%s-meta_attributes\">\
    <nvpair name=\"target-role\" id=\"%s-meta_attributes-target-role\" value=\"Stopped\"/>\
  </meta_attributes>\
  <operations id=\"%s-operations\">\
    <op id=\"%s-monitor-5\" interval=\"5\" name=\"monitor\" timeout=\"60\"/>\
    <op id=\"%s-start-0\" interval=\"0\" name=\"start\" timeout=\"300\"/>\
    <op id=\"%s-stop-0\" interval=\"0\" name=\"stop\" timeout=\"300\"/>\
  </operations>\
  <instance_attributes id=\"%s-instance_attributes\">\
    <nvpair id=\"%s-instance_attributes-target\" name=\"target\" value=\"%s\"/>\
  </instance_attributes>\
</primitive>" % (ha_label, ha_label, ha_label, ha_label, ha_label,
                 ha_label, ha_label, ha_label, ha_label, uuid))
        os.close(tmp_f)

        cibadmin(["-o", "resources", "-C", "-x", "%s" % tmp_name])
        score = 20
        preference = "primary"
    else:
        score = 10
        preference = "secondary"

    rc, stdout, stderr = cibadmin(["-o", "constraints", "-C", "-X",
                                   "<rsc_location id=\"%s-%s\" node=\"%s\" rsc=\"%s\" score=\"%s\"/>" %
                                   (ha_label, preference, os.uname()[1],
                                    ha_label, score)])

    if rc == 76:
        raise RuntimeError("A constraint with the name %s-%s already exists" % (ha_label, preference))

    _mkdir_p_concurrent(mount_point)


def _get_nvpairid_from_xml(xml_string):
    import xml.etree.ElementTree as et
    doc = et.fromstring(xml_string)
    nodes = doc.findall('instance_attributes/nvpair')
    node = [x for x in nodes if x.attrib.get('name') == 'target']
    return node[0].get('value')


def _query_ha_targets():
    targets = {}

    rc, stdout, stderr = shell.run(['crm_resource', '-l'])
    if rc == 234:
        return targets
    elif rc != 0:
        raise RuntimeError("Error %s running crm_resource -l: %s %s" % (rc, stdout, stderr))
    else:
        for resource_id in stdout.split("\n"):
            if len(resource_id) < 1:
                continue

            target = {'ha_label': resource_id}
            raw_xml = "\n".join(shell.try_run(['crm_resource', '-r', resource_id, '-q']).split("\n")[2:])
            target['uuid'] = _get_nvpairid_from_xml(raw_xml)
            targets[resource_id] = target

        return targets


def mount_target(uuid):
    # these are called by the Target RA from corosync
    info = _get_target_config(uuid)

    filesystem = FileSystem(info['backfstype'], info['bdev'])

    filesystem.mount(info['target_name'], info['mntpt'])


def unmount_target(uuid):
    info = _get_target_config(uuid)

    filesystem = FileSystem(info['backfstype'], info['bdev'])

    filesystem.umount(info['target_name'], info['mntpt'])


def start_target(ha_label):
    from time import sleep
    # HYD-1989: brute force, try up to 3 times to start the target
    i = 0
    while True:
        i += 1
        shell.try_run(['crm_resource', '-r', ha_label, '-p', 'target-role',
                       '-m', '-v', 'Started'])

        # now wait for it to start
        timeout = 100
        n = 0
        while n < timeout:
            if get_resource_location(ha_label):
                break

            sleep(1)
            n += 1

        # and make sure it didn't start but (the RA) fail(ed)
        stdout = shell.try_run(['crm_mon', '-1'])

        failed = True
        for line in stdout.split("\n"):
            if line.lstrip().startswith(ha_label):
                if line.find("FAILED") < 0:
                    failed = False

        if failed:
            # try to leave things in a sane state for a failed mount
            shell.try_run(['crm_resource', '-r', ha_label, '-p',
                           'target-role', '-m', '-v', 'Stopped'])
            if i < 4:
                console_log.info("failed to start target %s" % ha_label)
            else:
                raise RuntimeError("failed to start target %s" % ha_label)

        else:
            location = get_resource_location(ha_label)
            if not location:
                raise RuntimeError("Started %s but now can't locate it!" % ha_label)
            return {'location': location}


def stop_target(ha_label):
    _stop_target(ha_label)


def _stop_target(ha_label):
    from time import sleep
    shell.try_run(['crm_resource', '-r', ha_label, '-p', 'target-role',
                  '-m', '-v', 'Stopped'])

    # now wait for it to stop
    timeout = 100
    n = 0
    while n < timeout:
        if not get_resource_location(ha_label):
            break
        sleep(1)
        n += 1

    if n == timeout:
        raise RuntimeError("failed to stop target %s" % ha_label)


# common plumbing for failover/failback
def _move_target(target_label, dest_node):
    from time import sleep
    arg_list = ["crm_resource", "--resource", target_label, "--move", "--node", dest_node]
    rc, stdout, stderr = shell.run(arg_list)

    if rc != 0:
        raise RuntimeError("Error (%s) running '%s': '%s' '%s'" % (rc, " ".join(arg_list), stdout, stderr))

    if stderr.find("%s is already active on %s\n" %
                   (target_label, dest_node)) > -1:
        return

    # now wait for it to complete its move
    timeout = 100
    n = 0
    migrated = False
    while n < timeout:
        if get_resource_location(target_label) == dest_node:
            migrated = True
            break
        sleep(1)
        n += 1

    # now delete the constraint that crm_resource --move created
    shell.try_run(["crm_resource", "--resource", target_label, "--un-move",
                   "--node", dest_node])
    if not migrated:
        raise RuntimeError("failed to fail back target %s" % target_label)


def find_resource_constraint(ha_label, disp):
    stdout = shell.try_run(["crm_resource", "-r", ha_label, "-a"])

    for line in stdout.rstrip().split("\n"):
        match = re.match("\s+:\s+Node\s+([^\s]+)\s+\(score=\d+, id=%s-%s\)" %
                         (ha_label, disp), line)
        if match:
            return match.group(1)

    return None


def failover_target(ha_label):
    """
    Fail a target over to its secondary node
    """
    node = find_resource_constraint(ha_label, "secondary")
    if not node:
        raise RuntimeError("Unable to find the secondary server for '%s'" %
                           ha_label)

    return _move_target(ha_label, node)


def failback_target(ha_label):
    """
    Fail a target back to its primary node
    """
    node = find_resource_constraint(ha_label, "primary")
    if not node:
        raise RuntimeError("Unable to find the primary server for '%s'" %
                           ha_label)
    return _move_target(ha_label, node)


def _get_target_config(uuid):
    info = config.get('targets', uuid)

    # Some history, previously the backfstype and target_name were not stored. So if not present presume ldiskfs
    # and for the target_name set as unknown because ldiskfs does not use it.
    if 'backfstype' not in info:
        info['backfstype'] = 'ldiskfs'
        info['target_name'] = 'unknown'
        config.update('targets', uuid, info)

    return info


#  FIXME: these appear to be unused, remove?
# def migrate_target(ha_label, node):
#     # a migration scores at 500 to force it higher than stickiness
#     score = 500
#     shell.try_run(["crm", "configure", "location", "%s-migrated" % ha_label, ha_label, "%s:" % score, "%s" % node])
#
#     shell.try_run(['crm_resource', '-r', ha_label, '-p', 'target-role',
#                    '-m', '-v', 'Stopped'])
#     shell.try_run(['crm_resource', '-r', ha_label, '-p', 'target-role',
#                    '-m', '-v', 'Started'])
#
#
# def unmigrate_target(ha_label):
#     from time import sleep
#
#     # just remove the migration constraint
#     shell.try_run(['crm', 'configure', 'delete', '%s-migrated' % ha_label])
#     sleep(1)
#
#     shell.try_run(['crm_resource', '-r', ha_label, '-p', 'target-role',
#                    '-m', '-v', 'Stopped'])
#     shell.try_run(['crm_resource', '-r', ha_label, '-p', 'target-role',
#                    '-m', '-v', 'Started'])


def target_running(uuid):
    from os import _exit
    from chroma_agent.utils import Mounts
    try:
        info = _get_target_config(uuid)
    except (KeyError, TypeError):
        # it can't possibly be running here if the config entry for
        # it doesn't even exist, or if the store doesn't even exist!
        _exit(1)

    def devices_match(a, b):
        return os.stat(a).st_ino == os.stat(b).st_ino

    mounts = Mounts()
    for device, mntpnt, fstype in mounts.all():
        if mntpnt == info['mntpt'] and devices_match(device, info['bdev']):
            _exit(0)

    _exit(1)


def clear_targets(force = False):
    if not force:
        from os import _exit
        import textwrap
        warning = """
        clear-targets will forcibly unmount and unconfigure all Lustre targets
        on EVERY node in this HA domain.  This is an irreversible and
        potentially very destructive operation.  Data loss may occur.  Please
        do not use it unless you fully understand the consequences!  If you
        are sure that this command does what you intend to do, then you must
        supply the --force flag to avoid seeing this message.
        """
        console_log.warn(textwrap.fill(textwrap.dedent(warning)))
        _exit(1)

    for resource, attrs in _query_ha_targets().items():
        console_log.info("Stopping %s" % resource)
        _stop_target(attrs['ha_label'])
        console_log.info("Unconfiguring %s" % resource)
        unconfigure_target_ha(True, attrs['ha_label'], attrs['uuid'])


def purge_configuration(device, filesystem_name):
    ls = shell.try_run(["debugfs", "-w", "-R", "ls -l CONFIGS/", device])

    victims = []
    for line in ls.split("\n"):
        try:
            name = line.split()[8]
        except IndexError:
            continue

        if name.startswith("%s-" % filesystem_name):
            victims.append(name)

    daemon_log.info("Purging config files: %s" % victims)

    for victim in victims:
        shell.try_run(["debugfs", "-w", "-R", "rm CONFIGS/%s" % victim, device])


ACTIONS = [purge_configuration, register_target, configure_target_ha,
           unconfigure_target_ha, mount_target, unmount_target,
           start_target, stop_target, format_target, check_block_device,
           writeconf_target, failback_target,
           failover_target, target_running,
           # migrate_target, unmigrate_target,
           clear_targets, configure_target_store, unconfigure_target_store]
