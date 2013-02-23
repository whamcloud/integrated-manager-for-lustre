#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import errno
import os
import re
import tempfile

from chroma_agent.log import daemon_log, console_log
from chroma_agent.store import AgentStore
from chroma_agent import shell
from chroma_agent.action_plugins.manage_corosync import cibadmin


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
    try:
        rc, stdout, stderr = shell.run(['crm_resource', '--locate', '--resource', resource_name])
    except OSError:
        # Probably we're on a server without corosync
        return None

    if rc != 0:
        # We can't get the state of the resource, assume that means it's not running (maybe
        # it was unconfigured while we were running)
        return None
    elif len(stdout.strip()) == 0:
        return None
    else:
        try:
            # Amusingly (?) corosync will sometimes report that a target is running on more than one
            # node, by outputting a number of 'is running on' lines.
            # This happens while we are adding a target -- a separate process doing a get_resource_locations
            # sees one of these multi-line outputs from 'crm_resource --locate'
            # this actually shouldn't happen any more with HYD-514 fixed
            line_count = len(stdout.strip().split('\n'))
            if line_count > 1:
                return None

            node_name = re.search("^resource [^ ]+ is running on: (.*)$", stdout.strip()).group(1)
        except AttributeError:
            raise RuntimeError("Bad crm_resource output '%s'" % stdout.strip())
        return node_name


def get_resource_locations():
    """Parse `crm resource list` to identify where (if anywhere)
       resources (i.e. targets) are running."""

    try:
        from crm.cibstatus import CibStatus
    except ImportError:
        # Corosync not installed
        return None

    cs = CibStatus.getInstance()
    status = cs.get_status()
    if not status:
        # Corosync not running
        return None
    member_of_cluster = len(status.childNodes) > 0

    locations = {}
    rc, lines_text, stderr = shell.run(["crm_resource", "--list-cts"])
    if rc != 0:
        # Corosync not running
        return None

    for line in lines_text.split("\n"):
        if line.startswith("Resource:"):
            #    printf("Resource: %s %s %s %s %s %s %s %s %d %lld 0x%.16llx\n",
            #        crm_element_name(rsc->xml), rsc->id,
            #        rsc->clone_name?rsc->clone_name:rsc->id, rsc->parent?rsc->parent->id:"NA",
            #        rprov?rprov:"NA", rclass, rtype, host?host:"NA", needs_quorum, rsc->flags, rsc->flags);

            preamble, el_name, rsc_id, rsc_clone_name, parent, provider, klass, type, host, needs_quorum, flags_dec, flags_hex = line.split()
            if provider == "chroma" and klass == "ocf" and type == "Target":
                if host != "NA":
                    node = host
                else:
                    node = None
                locations[rsc_id] = node

    if not member_of_cluster:
        # I can only make positive statements
        # that a resource is running on this node, not negative statements
        # that it's not running at all
        locations = dict((k, v) for k, v in locations.items() if v is not None)

    return locations


def format_target(device=None, target_types=(), mgsnode=(), fsname=None, failnode=(),
         servicenode=(), param={}, index=None, comment=None, mountfsoptions=None,
         network=(), backfstype=None, device_size=None, mkfsoptions=None,
         reformat=False, stripe_count_hint=None, iam_dir=False,
         dryrun=False, verbose=False, quiet=False):
    """Perform a mkfs.lustre operation on a block device."""

    # freeze a view of the namespace before we start messing with it
    args = dict(locals())
    options = []

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

    shell.try_run(['mkfs.lustre'] + options + [device])

    blkid_output = shell.try_run(["blkid", "-o", "value", "-s", "UUID", device])
    uuid = blkid_output.strip()

    dumpe2fs_output = shell.try_run(["dumpe2fs", "-h", device])
    inode_count = int(re.search("Inode count:\\s*(\\d+)$", dumpe2fs_output, re.MULTILINE).group(1))
    inode_size = int(re.search("Inode size:\\s*(\\d+)$", dumpe2fs_output, re.MULTILINE).group(1))

    return {
            'uuid': uuid,
            'inode_size': inode_size,
            'inode_count': inode_count
    }


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


def register_target(mount_point, device):
    _mkdir_p_concurrent(mount_point)

    mount_args = ["mount", "-t", "lustre", device, mount_point]
    rc, stdout, stderr = shell.run(mount_args)
    if rc == 5:
        # HYD-1040: Sometimes we should retry on a failed registration
        shell.try_run(mount_args)
    elif rc != 0:
        raise RuntimeError("Error (%s) running '%s': '%s' '%s'" % (rc, " ".join(mount_args), stdout, stderr))

    shell.try_run(["umount", mount_point])

    blkid_output = shell.try_run(["blkid", "-c/dev/null", "-o", "value", "-s", "LABEL", device])

    return {'label': blkid_output.strip()}


def unconfigure_target_ha(primary, ha_label, uuid):
    if get_resource_location(ha_label):
        raise RuntimeError("cannot unconfigure-ha: %s is still running " %
                           ha_label)

    if primary:
        rc, stdout, stderr = cibadmin(["-D", "-X",
                                       "<rsc_location id=\"%s-primary\">" %
                                       ha_label])
        rc, stdout, stderr = cibadmin(["-D", "-X", "<primitive id=\"%s\">" %
                                       ha_label])
        rc, stdout, stderr = shell.run(['crm_resource', '--cleanup',
                                        '--resource', ha_label])

        if rc != 0 and rc != 234:
            raise RuntimeError("Error %s trying to cleanup resource %s" % (rc,
                               ha_label))

    else:
        rc, stdout, stderr = cibadmin(["-D", "-X",
                                       "<rsc_location id=\"%s-secondary\">" %
                                       ha_label])

    AgentStore.remove_target_info(uuid)


def configure_target_ha(primary, device, ha_label, uuid, mount_point):
    if primary:
        # If the target already exists with the same params, skip.
        # If it already exists with different params, that is an error
        rc, stdout, stderr = shell.run(["crm_resource", "-r", ha_label, "-g", "target"])
        if rc == 0:
            info = AgentStore.get_target_info(stdout.rstrip("\n"))
            if info['bdev'] == device and info['mntpt'] == mount_point:
                return
            else:
                raise RuntimeError("A resource with the name %s already exists" % ha_label)

    AgentStore.set_target_info(uuid, {"bdev": device, "mntpt": mount_point})

    if primary:
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

    rc, stdout, stderr = shell.run(['crm', '-D', 'plain', 'configure', 'show',
                                    '%s-%s' % (ha_label, preference)])
    out = stdout.rstrip("\n")

    node = os.uname()[1]

    if len(out) > 0:
        compare = "location %s-%s %s %s: %s" % (ha_label, preference,
                                                ha_label, score,
                                                node)
        if out == compare:
            return
        else:
            raise RuntimeError("A constraint with the name %s-%s already exists" % (ha_label, preference))

    rc, stdout, stderr = cibadmin(["-o", "constraints", "-C", "-X",
                                   "<rsc_location id=\"%s-%s\" node=\"%s\" rsc=\"%s\" score=\"%s\"/>" %
                                  (ha_label,
                                  preference,
                                  node,
                                  ha_label, score)])

    _mkdir_p_concurrent(mount_point)


def _get_nvpairid_from_xml(xml_string):
    import xml.etree.ElementTree as et
    doc = et.fromstring(xml_string)
    node = doc.find('instance_attributes/nvpair[@name="target"]')
    return node.get('value')


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
    info = AgentStore.get_target_info(uuid)
    shell.try_run(['mount', '-t', 'lustre', info['bdev'], info['mntpt']])


def unmount_target(uuid):
    info = AgentStore.get_target_info(uuid)
    shell.try_run(["umount", info['bdev']])


def start_target(ha_label):
    from time import sleep
    # do a cleanup first, just to clear any previously errored state
    shell.try_run(['crm', 'resource', 'cleanup', ha_label])
    shell.try_run(['crm_resource', '-r', ha_label, '-p', 'target-role',
                   '-m', '-v', 'Started'])

    # now wait for it to start
    # FIXME: this may break on non-english systems or new versions of pacemaker
    timeout = 100
    n = 0
    while n < timeout:
        stdout = shell.try_run(['crm', 'resource', 'status', ha_label])

        if stdout.startswith("resource %s is running on:" % ha_label):
            break

        sleep(1)
        n += 1

    # and make sure it didn't start but (the RA) fail(ed)
    stdout = shell.try_run(['crm', 'status'])

    failed = True
    for line in stdout.split("\n"):
        if line.startswith(" %s" % ha_label):
            if line.find("FAILED") < 0:
                failed = False

    if failed:
        # try to leave things in a sane state for a failed mount
        shell.try_run(['crm_resource', '-r', ha_label, '-p',
                       'target-role', '-m', '-v', 'Stopped'])
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

    # now wait for it
    # FIXME: this may break on non-english systems or new versions of pacemaker
    timeout = 100
    n = 0
    while n < timeout:
        arg_list = ["crm", "resource", "status", ha_label]
        rc, stdout, stderr = shell.run(arg_list)
        if rc != 0:
            raise RuntimeError("Error (%s) running '%s': '%s' '%s'" % (rc, " ".join(arg_list), stdout, stderr))
        if stderr.find("is NOT running") > -1:
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

    # now delete the constraint that crm resource move created
    shell.try_run(["crm", "configure", "delete", "cli-prefer-%s" % target_label])
    if not migrated:
        raise RuntimeError("failed to fail back target %s" % target_label)


def failover_target(ha_label):
    """
    Fail a target over to its secondary node
    """
    stdout = shell.try_run(["crm", "configure", "show", "%s-secondary" % ha_label])
    secondary = stdout[stdout.rfind(' ') + 1:-1]
    return _move_target(ha_label, secondary)


def failback_target(ha_label):
    """
    Fail a target back to its primary node
    """
    stdout = shell.try_run(["crm", "configure", "show", "%s-primary" % ha_label])
    primary = stdout[stdout.rfind(' ') + 1:-1]
    return _move_target(ha_label, primary)

# FIXME: these appear to be unused, remove?
#def migrate_target(ha_label, node):
#    # a migration scores at 500 to force it higher than stickiness
#    score = 500
#    shell.try_run(["crm", "configure", "location", "%s-migrated" % ha_label, ha_label, "%s:" % score, "%s" % node])
#
#    shell.try_run(['crm_resource', '-r', ha_label, '-p', 'target-role',
#                   '-m', '-v', 'Stopped'])
#    shell.try_run(['crm_resource', '-r', ha_label, '-p', 'target-role',
#                   '-m', '-v', 'Started'])
#
#
#def unmigrate_target(ha_label):
#    from time import sleep
#
#    # just remove the migration constraint
#    shell.try_run(['crm', 'configure', 'delete', '%s-migrated' % ha_label])
#    sleep(1)
#
#    shell.try_run(['crm_resource', '-r', ha_label, '-p', 'target-role',
#                   '-m', '-v', 'Stopped'])
#    shell.try_run(['crm_resource', '-r', ha_label, '-p', 'target-role',
#                   '-m', '-v', 'Started'])


def target_running(uuid):
    from os import _exit
    from chroma_agent.utils import Mounts
    try:
        info = AgentStore.get_target_info(uuid)
    except:
        # it can't possibly be running here if the AgentStore entry for
        # it doesn't even exist
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
           start_target, stop_target, format_target,
           writeconf_target, failback_target,
           failover_target, target_running,
           #migrate_target, unmigrate_target,
           clear_targets]
