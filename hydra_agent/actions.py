#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

""" Library of actions that the hydra-agent can be asked to carry out."""

from hydra_agent.legacy_audit import LocalLustreAudit
import errno
import os
import shlex, subprocess
import simplejson as json

LIBDIR = "/var/lib/hydra"

def create_libdir():
    try:
        os.makedirs(LIBDIR)
    except OSError, e:
        if e.errno == errno.EEXIST:
            pass
        else:
            raise e

def locate_device(args):
    lla = LocalLustreAudit()
    lla.read_mounts()
    lla.read_fstab()
    device_nodes = lla.get_device_nodes()
    node_result = None
    for d in device_nodes:
        if d['fs_uuid'] == args.uuid:
            node_result = d
    return node_result




def run(arg_list, shell = False):
    """Run a subprocess, and return a tuple of rc, stdout, stderr.

    Note: we buffer all output, so do not run commands with large outputs 
    using this function.
    """

    import sys
    import pty
    import fcntl, os
    import select

    # Create a PTY in order to get libc in child processes
    # to use line-buffered instead of buffered mode on stdout
    master, slave = pty.openpty()
    stdout_file = os.fdopen(master)

    p = subprocess.Popen(arg_list, shell = shell,
                         stdout = slave,
                         stderr = subprocess.PIPE,
                         close_fds = True)

    # Set O_NONBLOCK on stdout and stderr, in order to use select.poll later
    flags = fcntl.fcntl(master, fcntl.F_GETFL)
    fcntl.fcntl(master, fcntl.F_SETFL, flags | os.O_NONBLOCK)
    flags = fcntl.fcntl(p.stderr, fcntl.F_GETFL)
    fcntl.fcntl(p.stderr, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    # Create a poll object and register
    all_poll_flags = select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR | select.POLLNVAL
    poll = select.poll()
    poll.register(p.stderr, all_poll_flags)
    poll.register(master, all_poll_flags)

    # We will iterate on poll.poll until we have seen HUPs on both
    # stdout and stderr.
    stdout_buf = ""
    stderr_buf = ""

    stdout_closed = False
    stderr_closed = False
    while (not stdout_closed) and (not stderr_closed):
        result = poll.poll(100)
        for fd, mask in result:
            if fd == master and mask & (select.POLLIN | select.POLLPRI):
                import os
                stdout = stdout_file.read(select.PIPE_BUF)
                stdout_buf = stdout_buf + stdout
                sys.stderr.write(stdout)
            elif fd == p.stderr.fileno() and mask & (select.POLLIN | select.POLLPRI):
                stderr = p.stderr.read(select.PIPE_BUF)
                stderr_buf = stderr_buf + stderr
                sys.stderr.write(stderr)
            elif mask & select.POLLHUP:
                if fd == master:
                    stdout_closed = True
                elif fd == p.stderr.fileno():
                    stderr_closed = True
                else:
                    raise RuntimeError("Unexpected select() result %s" % ((fd, mask),))
            else:
                raise RuntimeError("Unexpected select() result %s" % ((fd, mask),))
    rc = p.poll()

    return rc, stdout_buf, stderr_buf


def try_run(arg_list, shell = False):
    """Run a subprocess, and raise an exception if it returns nonzero.  Return
    stdout string."""
    rc, stdout, stderr = run(arg_list, shell)
    if rc != 0:
        raise RuntimeError("Error running '%s': '%s' '%s'" % (" ".join(arg_list), stdout, stderr))

    return stdout

def format_target(args):
    from hydra_agent.cmds import lustre

    kwargs = json.loads(args.args)
    cmdline = lustre.mkfs(**kwargs)

    try_run(shlex.split(cmdline))

    blkid_output = try_run(["blkid", "-o", "value", "-s", "UUID", kwargs['device']])

    uuid = blkid_output.strip()

    return {'uuid': uuid}

def register_target(args):
    create_libdir()

    try:
        os.makedirs(args.mountpoint)
    except OSError, e:
        if e.errno == errno.EEXIST:
            pass
        else:
            raise e

    try_run(["mount", "-t", "lustre", args.device, args.mountpoint])
    try_run(["umount", args.mountpoint])
    blkid_output = try_run(["blkid", "-o", "value", "-s", "LABEL", args.device])

    return {'label': blkid_output.strip()}

def _mount_config_file(label):
    return os.path.join(LIBDIR, label)

def unconfigure_ha(args):
    # NB: 'crm configure delete' returns zero if it fails 
    # because the resource because it's running.  Helpful.
    # We do an ugly check on the stderr to detect the message
    # from that case.
    if args.primary:
        cmd = ["crm", "configure", "delete", args.label]
        rc, stdout, stderr = run(cmd)
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
            raise RuntimeError("Error unconfiguring %s: it is running" % (args.label))

    try:
        os.unlink(_mount_config_file(args.label))
    except OSError, e:
        if e.errno == errno.ENOENT:
            pass
        else:
            raise e

def configure_ha(args):
    if args.primary:
        # now configure pacemaker for this target
        # XXX - crm is a python script -- should look into interfacing
        #       with it directly
        try_run(shlex.split("crm configure primitive %s ocf:hydra:Target meta target-role=\"stopped\" operations \$id=\"%s-operations\" op monitor interval=\"120\" timeout=\"60\" op start interval=\"0\" timeout=\"300\" op stop interval=\"0\" timeout=\"300\" params target=\"%s\"" % (args.label, args.label, args.label)))
        score = 20
        preference = "primary"
    else:
        score = 10
        preference = "secondary"

    try_run(shlex.split("crm configure location %s-%s %s %s: %s" % \
                        (args.label, preference, args.label, score,
                         os.uname()[1])))

    create_libdir()

    try:
        os.makedirs(args.mountpoint)
    except OSError, e:
        if e.errno == errno.EEXIST:
            pass
        else:
            raise e

    # Save the metadata for the mount (may throw an IOError)
    file = open(_mount_config_file(args.label), 'w')
    json.dump({"bdev": args.device, "mntpt": args.mountpoint}, file)
    file.close()

def mount_target(args):
    try:
        file = open("%s/%s" % (LIBDIR, args.label), 'r')
        j = json.load(file)
        file.close()
    except IOError, e:
        raise RuntimeError("Failed to read target data for '%s', is it configured? (%s)" % (args.label, e))

    try_run(['mount', '-t', 'lustre', j['bdev'], j['mntpt']])

def unmount_target(args):
    try:
        file = open("%s/%s" % (LIBDIR, args.label), 'r')
        j = json.load(file)
        file.close()
    except IOError, e:
        raise RuntimeError("Failed to read target data for '%s', is it configured? (%s)" % (args.label, e))

    try_run(["umount", j['bdev']])

def start_target(args):
    try_run(["crm", "resource", "start", args.label])

    # now wait for it
    # FIXME: this may break on non-english systems or new versions of pacemaker
    try_run("while ! crm resource status %s 2>&1 | grep -q \"is running\"; do sleep 1; done" % \
            args.label, shell=True)

def stop_target(args):
    try_run(["crm", "resource", "stop", args.label])

    # now wait for it
    # FIXME: this may break on non-english systems or new versions of pacemaker
    try_run("while ! crm resource status %s 2>&1 | grep -q \"is NOT running\"; do sleep 1; done" % \
            args.label, shell=True)

def migrate_target(args):
    # a migration scores at 500 to force it higher than stickiness
    score = 500
    try_run(shlex.split("crm configure location %s-migrated %s %s: %s" % \
                        (args.label, args.label, score, args.node)))

def unmigrate_target(args):
    # just remove the migration constraint
    try_run("crm configure delete %s-migrated && (sleep 1; crm resource stop %s && crm resource start %s)" % \
                        (args.label, args.label, args.label), shell = True)

def fail_node(args):
    # force a manual failover by failing a node
    try_run("sync; sync; init 0", shell = True)

def audit(args):
    return LocalLustreAudit().audit_info()
