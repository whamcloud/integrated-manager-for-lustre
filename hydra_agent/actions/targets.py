
from hydra_agent.store import *
from hydra_agent import shell
import simplejson as json
import errno
import os
import shlex

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
    _unconfigure_ha(args.primary, args.label)

def _unconfigure_ha(primary, label):
    # NB: 'crm configure delete' returns zero if it fails 
    # because the resource because it's running.  Helpful.
    # We do an ugly check on the stderr to detect the message
    # from that case.
    if primary:
        cmd = ["crm", "configure", "delete", label]
        rc, stdout, stderr = shell.run(cmd)
        if rc != 0:
            if rc == 1 and stderr.find("does not exist") != -1:
                # Removing something which is already removed is
                # a success: idempotency.
                pass
            else:
                raise RuntimeError("Error running '%s': %s" % (cmd, stderr))
        elif stderr.find("is running, can't delete it") != -1:
            # Messages like: "WARNING: resource flintfs-MDT0000 is running, can't delete it"
            # FIXME: this conditional may break oWARNING: resource flintfs-MDT0000 is running, can't delete itn non-english
            # systems or new versions of pacemaker
            raise RuntimeError("Error unconfiguring %s: it is running" % (label))

    store_remove_target_info(label)

def configure_ha(args):
    if args.primary:
        # now configure pacemaker for this target
        # XXX - crm is a python script -- should look into interfacing
        #       with it directly
        shell.try_run(shlex.split("crm configure primitive %s ocf:hydra:Target meta target-role=\"stopped\" operations \$id=\"%s-operations\" op monitor interval=\"120\" timeout=\"60\" op start interval=\"0\" timeout=\"300\" op stop interval=\"0\" timeout=\"300\" params target=\"%s\"" % (args.label, args.label, args.label)))
        score = 20
        preference = "primary"
    else:
        score = 10
        preference = "secondary"

    shell.try_run(shlex.split("crm configure location %s-%s %s %s: %s" % \
                        (args.label, preference, args.label, score,
                         os.uname()[1])))

    try:
        os.makedirs(args.mountpoint)
    except OSError, e:
        if e.errno == errno.EEXIST:
            pass
        else:
            raise e

    store_write_target_info(args.label, {"bdev": args.device, "mntpt": args.mountpoint})

def mount_target(args):
    info = store_get_target_info(args.label)
    shell.try_run(['mount', '-t', 'lustre', info['bdev'], info['mntpt']])

def unmount_target(args):
    info = store_get_target_info(args.label)
    shell.try_run(["umount", info['bdev']])

def start_target(args):
    shell.try_run(["crm", "resource", "start", args.label])

    # now wait for it
    # FIXME: this may break on non-english systems or new versions of pacemaker
    shell.try_run("while ! crm resource status %s 2>&1 | grep -q \"is running\"; do sleep 1; done" % \
            args.label, shell=True)

def stop_target(args):
    _stop_target(args.label)

def _stop_target(label):
    shell.try_run(["crm", "resource", "stop", label])

    # now wait for it
    # FIXME: this may break on non-english systems or new versions of pacemaker
    shell.try_run("while ! crm resource status %s 2>&1 | grep -q \"is NOT running\"; do sleep 1; done" % \
            label, shell=True)

def migrate_target(args):
    # a migration scores at 500 to force it higher than stickiness
    score = 500
    shell.try_run(shlex.split("crm configure location %s-migrated %s %s: %s" % \
                        (args.label, args.label, score, args.node)))

def unmigrate_target(args):
    # just remove the migration constraint
    shell.try_run("crm configure delete %s-migrated && (sleep 1; crm resource stop %s && crm resource start %s)" % \
                        (args.label, args.label, args.label), shell = True)


