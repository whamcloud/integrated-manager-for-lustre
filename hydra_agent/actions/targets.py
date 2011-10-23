
from hydra_agent.store import *
from hydra_agent import shell
import simplejson as json
import errno
import os
import shlex
import re

LIBDIR = "/var/lib/hydra"

def create_libdir():
    try:
        os.makedirs(LIBDIR)
    except OSError, e:
        if e.errno == errno.EEXIST:
            pass
        else:
            raise e

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
        node_name = re.search("^resource [^ ]+ is running on: (.*)$", stdout.strip()).group(1)
        return node_name

def get_resource_locations():
    """Parse `corosync status` to identify where (if anywhere) 
       resources (i.e. targets) are running."""
    try:
        rc, stdout, stderr = shell.run(['crm_resource', '-l'])
    except OSError:
        # Probably we're on a server without corosync
        return None

    locations = {}

    if rc != 0:
        # Probably corosync isn't running?
        return None
    else:
        lines = stdout.strip().split("\n")
        for line in lines:
            resource_name = line.strip()
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
    from hydra_agent.cmds import lustre

    kwargs = json.loads(args.args)
    cmdline = lustre.mkfs(**kwargs)

    shell.try_run(shlex.split(cmdline))

    blkid_output = shell.try_run(["blkid", "-o", "value", "-s", "UUID", kwargs['device']])
    uuid = blkid_output.strip()

    return {'uuid': uuid}

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
    blkid_output = shell.try_run(["blkid", "-o", "value", "-s", "LABEL", args.device])
    if blkid_output.find("ffff") != -1:
        # Oh hey, we reproduced HYD-268, see if the tunefs output is any different from the blkid output
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
    _unconfigure_ha(args.primary, args.label, args.serial)

def _unconfigure_ha(primary, label, serial):
    unique_label = "%s_%s" % (label, serial)
    if primary:
        rc, stdout, stderr = cibadmin("-D -X '<rsc_location id=\"%s-primary\">'" % unique_label)
        rc, stdout, stderr = cibadmin("-D -X '<primitive id=\"%s\">'" % unique_label)
    else:
        rc, stdout, stderr = cibadmin("-D -X '<rsc_location id=\"%s-secondary\">'" % unique_label)

    store_remove_target_info(label)

def configure_ha(args):
    unique_label = "%s_%s" % (args.label, args.serial)
    if args.primary:
        # now configure pacemaker for this target
        from tempfile import mkstemp
        tmp_f, tmp_name = mkstemp()
        os.write(tmp_f, "<primitive class=\"ocf\" provider=\"hydra\" type=\"Target\" id=\"%s\">\
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
            unique_label, unique_label, unique_label, unique_label, args.label))
        os.close(tmp_f)

        rc, stdout, stderr = cibadmin("-o resources -C -x %s" % tmp_name)
        score = 20
        preference = "primary"
    else:
        score = 10
        preference = "secondary"

    rc, stdout, stderr = cibadmin("-o constraints -C -X '<rsc_location id=\"%s-%s\" node=\"%s\" rsc=\"%s\" score=\"%s\"/>'" % (unique_label,
                                  preference,
                                  os.uname()[1],
                                  unique_label, score))

    create_libdir()

    try:
        os.makedirs(args.mountpoint)
    except OSError, e:
        if e.errno == errno.EEXIST:
            pass
        else:
            raise e

    store_write_target_info(args.label, {"bdev": args.device, "mntpt": args.mountpoint})

def list_ha_targets(args):
    targets = []
    for line in shell.try_run("crm resource list", shell=True).split("\n"):
        match = re.match(r"^\s*([^\s]+).+hydra:Target", line)
        if match:
            targets.append(match.groups()[0])

    return targets

def mount_target(args):
    info = store_get_target_info(args.label)
    shell.try_run(['mount', '-t', 'lustre', info['bdev'], info['mntpt']])

def unmount_target(args):
    info = store_get_target_info(args.label)
    shell.try_run(["umount", info['bdev']])

def start_target(args):
    from time import sleep
    unique_label = "%s_%s" % (args.label, args.serial)
    shell.try_run(["crm", "resource", "start", unique_label])

    # now wait for it to start
    # FIXME: this may break on non-english systems or new versions of pacemaker
    timeout = 100
    n = 0
    while n < timeout:
        stdout = shell.try_run("crm resource status %s 2>&1" % unique_label,
                               shell=True)
        if stdout.startswith("resource %s is running on:" % unique_label):
            break
        sleep(1)
        n += 1

    # and make sure it didn't start but (the RA) fail(ed)
    stdout = shell.try_run("crm status", shell=True)

    failed = True
    for line in stdout.split("\n"):
        if line.startswith(" %s" % unique_label):
            if line.find("FAILED") < 0:
                failed = False

    if failed:
        # try to leave things in a sane state for a failed mount
        shell.try_run(["crm", "resource", "stop", unique_label])
        raise RuntimeError("failed to start target %s" % unique_label)
    else:
        location = get_resource_location(unique_label)
        if not location:
            raise RuntimeError("Started %s but now can't locate it!" % unique_label)
        return {'location': location}

def stop_target(args):
    _stop_target(args.label, args.serial)

def _stop_target(label, serial):
    unique_label = "%s_%s" % (label, serial)
    from time import sleep
    shell.try_run(["crm", "resource", "stop", unique_label])

    # now wait for it
    # FIXME: this may break on non-english systems or new versions of pacemaker
    timeout = 100
    n = 0
    while n < timeout:
        stdout = shell.try_run("crm resource status %s 2>&1" % unique_label, shell=True)
        if stdout.find("is NOT running") > -1:
            break
        sleep(1)
        n += 1

    if n == timeout:
        raise RuntimeError("failed to stop target %s" % unique_label)

def migrate_target(args):
    # a migration scores at 500 to force it higher than stickiness
    score = 500
    shell.try_run(shlex.split("crm configure location %s-migrated %s %s: %s" % \
                        (args.label, args.label, score, args.node)))

def unmigrate_target(args):
    # just remove the migration constraint
    shell.try_run("crm configure delete %s-migrated && (sleep 1; crm resource stop %s && crm resource start %s)" % \
                        (args.label, args.label, args.label), shell = True)
