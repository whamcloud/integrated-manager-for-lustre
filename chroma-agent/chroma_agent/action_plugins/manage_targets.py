#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from chroma_agent.plugins import ActionPlugin
from chroma_agent.store import AgentStore
from chroma_agent import shell
import simplejson as json
import errno
import os
import shlex
import re
import libxml2


def __sanitize_arg(arg):
    """Private function to safely quote arguments containing whitespace."""
    if re.search(r'\s', arg):
        arg = '"%s"' % arg

    return arg


def tunefs(device="", target_types=(), mgsnode=(), fsname="", failnode=(),
           servicenode=(), param={}, index="", comment="", mountfsoptions="",
           network=(), erase_params=False, nomgs=False, writeconf=False,
           dryrun=False, verbose=False, quiet=False):
    """Returns shell code for performing a tunefs.lustre operation on a
    block device."""

    # freeze a view of the namespace before we start messing with it
    args = locals()
    types = []
    options = []

    tuple_options = "target_types mgsnode failnode servicenode network".split()
    for name in tuple_options:
        arg = args[name]
        # ensure that our tuple arguments are always tuples, and not strings
        if not hasattr(arg, "__iter__"):
            arg = (arg,)

        if name == "target_types":
            for type in arg:
                types.append("--%s" % type)
        else:
            if len(arg) > 0:
                options.append("--%s=%s" % (name, ",".join(arg)))

    flag_options = {
        'erase_params': '--erase-params',
        'nomgs': '--nomgs',
        'writeconf': '--writeconf',
        'dryrun': '--dryrun',
        'verbose': '--verbose',
        'quiet': '--quiet',
    }
    for arg in flag_options:
        if args[arg]:
            options.append("%s" % flag_options[arg])

    dict_options = "param".split()
    for name in dict_options:
        arg = args[name]
        for key in arg:
            if arg[key] is not None:
                options.append("--%s %s=%s" % (name, key, __sanitize_arg(arg[key])))

    # everything else
    handled = set(flag_options.keys() + tuple_options + dict_options)
    for name in set(args.keys()) - handled:
        if name == "device":
            continue
        value = args[name]
        if value != '':
            options.append("--%s=%s" % (name, __sanitize_arg(value)))

    # NB: Use $PATH instead of relying on hard-coded paths
    cmd = "tunefs.lustre %s %s %s" % (" ".join(types), " ".join(options), device)

    return ' '.join(cmd.split())


def mkfs(device="", target_types=(), mgsnode=(), fsname="", failnode=(),
         servicenode=(), param={}, index="", comment="", mountfsoptions="",
         network=(), backfstype="", device_size="", mkfsoptions="",
         reformat=False, stripe_count_hint="", iam_dir=False,
         dryrun=False, verbose=False, quiet=False):
    """Returns shell code for performing a mkfs.lustre operation on a
    block device."""

    # freeze a view of the namespace before we start messing with it
    args = locals()
    types = []
    options = []

    tuple_options = "target_types mgsnode failnode servicenode network".split()
    for name in tuple_options:
        arg = args[name]
        # ensure that our tuple arguments are always tuples, and not strings
        if not hasattr(arg, "__iter__"):
            arg = (arg,)

        if name == "target_types":
            for type in arg:
                types.append("--%s" % type)
        elif name == 'mgsnode':
            for mgsnode in arg:
                options.append("--%s=%s" % (name, mgsnode))
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

    dict_options = "param".split()
    for name in dict_options:
        arg = args[name]
        for key in arg:
            if arg[key] is not None:
                options.append("--%s %s=%s" % (name, key, __sanitize_arg(arg[key])))

    # everything else
    handled = set(flag_options.keys() + tuple_options + dict_options)
    for name in set(args.keys()) - handled:
        if name == "device":
            continue
        value = args[name]
        if value != '':
            options.append("--%s=%s" % (name, __sanitize_arg(value)))

    # NB: Use $PATH instead of relying on hard-coded paths
    cmd = "mkfs.lustre %s %s %s" % (" ".join(types), " ".join(options), device)

    return ' '.join(cmd.split())


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
        rc, stdout, stderr = shell.run(['crm', 'resource', 'list'])
    except OSError:
        # Probably we're on a server without corosync
        return None

    locations = {}

    if stdout.strip() == "NO resources configured":
        return {}
    elif rc != 0:
        # Probably corosync isn't running?
        return None
    else:
        lines = stdout.strip().split("\n")
        for line in lines:
            [resource_name, resource_type] = line.strip().split("\t")
            if resource_type.startswith("(ocf::chroma:Target)"):
                locations[resource_name] = get_resource_location(resource_name)

    return locations


def cibadmin(command_args):
    from time import sleep

    # try at most, 100 times
    n = 100
    rc = 10

    while rc == 10 and n > 0:
        rc, stdout, stderr = shell.run(shlex.split("cibadmin " + command_args))
        if rc == 0:
            break
        sleep(1)
        n -= 1

    if rc != 0:
        raise RuntimeError("Error (%s) running 'cibadmin %s': '%s' '%s'" % \
                           (rc, command_args, stdout, stderr))

    return rc, stdout, stderr


def format_target(args):
    kwargs = json.loads(args.args)
    cmdline = mkfs(**kwargs)

    shell.try_run(shlex.split(cmdline))

    blkid_output = shell.try_run(["blkid", "-o", "value", "-s", "UUID", kwargs['device']])
    uuid = blkid_output.strip()

    dumpe2fs_output = shell.try_run(["dumpe2fs", "-h", kwargs['device']])
    inode_count = int(re.search("Inode count:\\s*(\\d+)$", dumpe2fs_output, re.MULTILINE).group(1))
    inode_size = int(re.search("Inode size:\\s*(\\d+)$", dumpe2fs_output, re.MULTILINE).group(1))

    return {
            'uuid': uuid,
            'inode_size': inode_size,
            'inode_count': inode_count
            }


def register_target(args):
    try:
        os.makedirs(args.mountpoint)
    except OSError, e:
        if e.errno == errno.EEXIST:
            pass
        else:
            raise e

    shell.try_run(["mount", "-t", "lustre", args.device, args.mountpoint])
    shell.try_run(["umount", args.mountpoint])
    blkid_output = shell.try_run(["blkid", "-c/dev/null", "-o", "value", "-s", "LABEL", args.device])
    if blkid_output.find("ffff") != -1:
        # Oh hey, we reproduced HYD-268, see if the tunefs output is any different from the blkid output
        # This shouldn't happen, although before we added '-c/dev/null' it did occasionally.
        # Leaving this check here so that we can confirm things are okay -- time of writing is Nov2011,
        # if you're reading this more than a couple of months later then cull this branch.
        import subprocess
        tunefs_text = subprocess.Popen(["tunefs.lustre", "--dryrun", args.device], stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.read()
        name = re.search("Target:\\s+(.*)\n", tunefs_text).group(1)
        # Now let's see if we get a different answer after 5 seconds
        import time
        time.sleep(5)
        blkid_later = shell.try_run(["blkid", "-o", "value", "-s", "LABEL", args.device])
        raise RuntimeError("HYD-268 (%s, %s, %s)" % (blkid_output.strip(), name, blkid_later.strip()))

    return {'label': blkid_output.strip()}


def unconfigure_ha(args):
    _unconfigure_ha(args.primary, args.label, args.uuid, args.id)


def _unconfigure_ha(primary, label, uuid, id):
    unique_label = "%s_%s" % (label, id)

    if get_resource_location(unique_label):
        raise RuntimeError("cannot unconfigure-ha: %s is still running " % \
                           unique_label)

    if primary:
        rc, stdout, stderr = cibadmin("-D -X '<rsc_location id=\"%s-primary\">'" % unique_label)
        rc, stdout, stderr = cibadmin("-D -X '<primitive id=\"%s\">'" % unique_label)
        rc, stdout, stderr = shell.run(['crm_resource', '--cleanup', '--resource',
                       unique_label])

        if rc != 0 and rc != 234:
            raise RuntimeError("Error %s trying to cleanup resource %s" % (rc, unique_label))

    else:
        rc, stdout, stderr = cibadmin("-D -X '<rsc_location id=\"%s-secondary\">'" % unique_label)

    AgentStore.remove_target_info(uuid)


def configure_ha(args):
    unique_label = "%s_%s" % (args.label, args.id)

    if args.primary:
        # now configure pacemaker for this target
        from tempfile import mkstemp
        # but first see if this resource exists and matches what we are adding
        rc, stdout, stderr = shell.run(shlex.split("crm_resource -r %s -g target" % unique_label))
        if rc == 0:
            info = AgentStore.get_target_info(stdout.rstrip("\n"))
            if info['bdev'] == args.device and info['mntpt'] == args.mountpoint:
                return
            else:
                raise RuntimeError("A resource with the name %s already exists" % unique_label)

        tmp_f, tmp_name = mkstemp()
        os.write(tmp_f, "<primitive class=\"ocf\" provider=\"chroma\" type=\"Target\" id=\"%s\">\
  <meta_attributes id=\"%s-meta_attributes\">\
    <nvpair name=\"target-role\" id=\"%s-meta_attributes-target-role\" value=\"Stopped\"/>\
  </meta_attributes>\
  <operations id=\"%s-operations\">\
    <op id=\"%s-monitor-120\" interval=\"120\" name=\"monitor\" timeout=\"60\"/>\
    <op id=\"%s-start-0\" interval=\"0\" name=\"start\" timeout=\"300\"/>\
    <op id=\"%s-stop-0\" interval=\"0\" name=\"stop\" timeout=\"300\"/>\
  </operations>\
  <instance_attributes id=\"%s-instance_attributes\">\
    <nvpair id=\"%s-instance_attributes-target\" name=\"target\" value=\"%s\"/>\
  </instance_attributes>\
</primitive>" % (unique_label, unique_label, unique_label, unique_label, unique_label,
            unique_label, unique_label, unique_label, unique_label, args.uuid))
        os.close(tmp_f)

        rc, stdout, stderr = cibadmin("-o resources -C -x %s" % tmp_name)
        score = 20
        preference = "primary"
    else:
        score = 10
        preference = "secondary"

    rc, stdout, stderr = shell.run(['crm', '-D', 'plain', 'configure', 'show',
                                    '%s-%s' % (unique_label, preference)])
    out = stdout.rstrip("\n")

    node = os.uname()[1]

    if len(out) > 0:
        compare = "location %s-%s %s %s: %s" % (unique_label, preference,
                                                unique_label, score,
                                                node)
        if out == compare:
            return
        else:
            raise RuntimeError("A constraint with the name %s-%s already exists" % (unique_label, preference))

    rc, stdout, stderr = cibadmin("-o constraints -C -X '<rsc_location id=\"%s-%s\" node=\"%s\" rsc=\"%s\" score=\"%s\"/>'" % (unique_label,
                                  preference,
                                  node,
                                  unique_label, score))

    try:
        os.makedirs(args.mountpoint)
    except OSError, e:
        if e.errno == errno.EEXIST:
            pass
        else:
            raise e

    AgentStore.set_target_info(args.uuid, {"bdev": args.device, "mntpt": args.mountpoint})


def query_ha_targets(args):
    targets = {}

    for target in shell.try_run(['crm_resource', '-l']).split("\n"):
        if len(target) < 1:
            continue

        label, id = target.split("_")
        targets[target] = {'label': label, 'id': id}

        raw_xml = "\n".join(shell.try_run(['crm_resource', '-r', target, '-q']).split("\n")[2:])
        try:
            doc = libxml2.parseDoc(raw_xml)
            node = doc.xpathEval('//instance_attributes/nvpair[@name="target"]')[0]
            targets[target]['uuid'] = node.prop('value')
        except (ValueError, libxml2.parserError):
            continue

    return targets


def mount_target(args):
    # these are called by the Target RA from corosync
    info = AgentStore.get_target_info(args.uuid)
    shell.try_run(['mount', '-t', 'lustre', info['bdev'], info['mntpt']])


def unmount_target(args):
    info = AgentStore.get_target_info(args.uuid)
    shell.try_run(["umount", info['bdev']])


def start_target(args):
    from time import sleep
    unique_label = "%s_%s" % (args.label, args.id)
    shell.try_run(['crm_resource', '-r', unique_label, '-p', 'target-role',
                   '-m', '-v', 'Started'])

    # now wait for it to start
    # FIXME: this may break on non-english systems or new versions of pacemaker
    timeout = 100
    n = 0
    while n < timeout:
        stdout = shell.try_run("crm resource status %s 2>&1" % unique_label, shell=True)
        if stdout.startswith("resource %s is running on:" % unique_label):
            break
        sleep(1)
        n += 1

    # and make sure it didn't start but (the RA) fail(ed)
    stdout = shell.try_run(['crm', 'status'])

    failed = True
    for line in stdout.split("\n"):
        if line.startswith(" %s" % unique_label):
            if line.find("FAILED") < 0:
                failed = False

    if failed:
        # try to leave things in a sane state for a failed mount
        shell.try_run(['crm_resource', '-r', unique_label, '-p',
                       'target-role', '-m', '-v', 'Stopped'])
        raise RuntimeError("failed to start target %s" % unique_label)
    else:
        location = get_resource_location(unique_label)
        if not location:
            raise RuntimeError("Started %s but now can't locate it!" % unique_label)
        return {'location': location}


def stop_target(args):
    _stop_target(args.label, args.id)


def _stop_target(label, id):
    unique_label = "%s_%s" % (label, id)
    from time import sleep
    shell.try_run(['crm_resource', '-r', unique_label, '-p', 'target-role',
                  '-m', '-v', 'Stopped'])

    # now wait for it
    # FIXME: this may break on non-english systems or new versions of pacemaker
    timeout = 100
    n = 0
    while n < timeout:
        stdout = shell.try_run("crm resource status %s 2>&1" % unique_label,
                               shell=True)
        if stdout.find("is NOT running") > -1:
            break
        sleep(1)
        n += 1

    if n == timeout:
        raise RuntimeError("failed to stop target %s" % unique_label)


# fail a target back to it's primary node
def failback_target(args):
    from time import sleep
    unique_label = "%s_%s" % (args.label, args.id)
    stdout = shell.try_run(shlex.split("crm configure show %s-primary" %
                                       unique_label))
    primary = stdout[stdout.rfind(' ') + 1:-1]
    stdout = shell.try_run("crm_resource --resource %s --move --node %s 2>&1" % \
                           (unique_label, primary), shell = True)

    if stdout.find("%s is already active on %s\n" % \
                   (unique_label, primary)) > -1:
        return

    # now wait for it to complete its move
    timeout = 100
    n = 0
    migrated = False
    while n < timeout:
        if get_resource_location(unique_label) == primary:
            migrated = True
            break
        sleep(1)
        n += 1

    # now delete the constraint that crm resource move created
    shell.try_run(shlex.split("crm configure delete cli-prefer-%s" % \
                              unique_label))
    if not migrated:
        raise RuntimeError("failed to fail back target %s" % unique_label)


def migrate_target(args):
    # a migration scores at 500 to force it higher than stickiness
    score = 500
    shell.try_run(shlex.split("crm configure location %s-migrated %s %s: %s" % \
                        (args.label, args.label, score, args.node)))


def unmigrate_target(args):
    from time import sleep

    # just remove the migration constraint
    shell.try_run(['crm', 'configure', 'delete', '%s-migrated' % args.label])
    sleep(1)

    shell.try_run(['crm_resource', '-r', args.label, '-p', 'target-role',
                   '-m', '-v', 'Stopped'])
    shell.try_run(['crm_resource', '-r', args.label, '-p', 'target-role',
                   '-m', '-v', 'Started'])


def target_running(args):
    from os import _exit
    from chroma_agent.utils import Mounts
    try:
        info = AgentStore.get_target_info(args.uuid)
    except:
        # it can't possibly be running here if the AgentStore entry for
        # it doesn't even exist
        _exit(1)

    mounts = Mounts()
    for device, mntpnt, fstype in mounts.all():
        if device == info['bdev'] and mntpnt == info['mntpt']:
            _exit(0)

    _exit(1)


def clear_targets(args):
    for resource, attrs in query_ha_targets(args).items():
        print "Stopping %s" % resource
        _stop_target(attrs['label'], attrs['id'])
        print "Unconfiguring %s" % resource
        _unconfigure_ha(True, attrs['label'], attrs['uuid'], attrs['id'])


class TargetsPlugin(ActionPlugin):
    def register_commands(self, parser):
        p = parser.add_parser('register-target', help='register a target')
        p.add_argument('--device', required=True, help='device for target')
        p.add_argument('--mountpoint', required=True, help='mountpoint for target')
        p.set_defaults(func=register_target)

        p = parser.add_parser('configure-ha',
                                  help='configure a target\'s HA parameters')
        p.add_argument('--device', required=True, help='device of the target')
        p.add_argument('--label', required=True, help='label of the target')
        p.add_argument('--uuid', required=True, help='uuid of the target')
        p.add_argument('--id', required=True, help='id of the target')
        p.add_argument('--primary', action='store_true',
                       help='target is primary on this node')
        p.add_argument('--mountpoint', required=True, help='mountpoint for target')
        p.set_defaults(func=configure_ha)

        p = parser.add_parser('unconfigure-ha',
                                  help='unconfigure a target\'s HA parameters')
        p.add_argument('--label', required=True, help='label of the target')
        p.add_argument('--uuid', required=True, help='uuid of the target')
        p.add_argument('--id', required=True, help='id of target')
        p.add_argument('--primary', action='store_true',
                       help='target is primary on this node')
        p.set_defaults(func=unconfigure_ha)

        p = parser.add_parser('mount-target', help='mount a target')
        p.add_argument('--uuid', required=True, help='uuid of target to mount')
        p.set_defaults(func=mount_target)

        p = parser.add_parser('unmount-target', help='unmount a target')
        p.add_argument('--uuid', required=True,
                       help='uuid of target to unmount')
        p.set_defaults(func=unmount_target)

        p = parser.add_parser('start-target', help='start a target')
        p.add_argument('--label', required=True,
                       help='label of target to start')
        p.add_argument('--id', required=True,
                       help='id of target to start')
        p.set_defaults(func=start_target)

        p = parser.add_parser('stop-target', help='stop a target')
        p.add_argument('--label', required=True,
                       help='label of target to stop')
        p.add_argument('--id', required=True,
                       help='id of target to stop')
        p.set_defaults(func=stop_target)

        p = parser.add_parser('format-target', help='format a target')
        p.add_argument('--args', required=True, help='format arguments')
        p.set_defaults(func=format_target)

        p = parser.add_parser('migrate-target',
                              help='migrate a target to a node')
        p.add_argument('--label', required=True,
                       help='label of target to migrate')
        p.add_argument('--node', required=True,
                       help='node to migrate target to')
        p.set_defaults(func=migrate_target)

        p = parser.add_parser('failback-target',
                              help='fail a target back to it\'s primary node')
        p.add_argument('--label', required=True,
                       help='label of target to migrate')
        p.add_argument('--id', required=True,
                       help='id of target to stop')
        p.set_defaults(func=failback_target)

        p = parser.add_parser('unmigrate-target',
                              help='cancel prevous target migrate')
        p.add_argument('--label', required=True,
                       help='label of target to cancel migration of')
        p.set_defaults(func=unmigrate_target)

        p = parser.add_parser('target-running',
                              help='check if a target is running')
        p.add_argument('--uuid', required=True,
                       help='uuid of target to check')
        p.set_defaults(func=target_running)

        p = parser.add_parser("clear-targets",
                              help="clear targets from HA config")
        p.set_defaults(func=clear_targets)
