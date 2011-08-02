
from celery.decorators import task

from configure.lib.job import Job, Step, StepPaused, STEP_PAUSE_DELAY

def debug_ssh(host, command):
    ssh_monitor = host.monitor.downcast()

    import paramiko
    import socket
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    from settings import AUDIT_PERIOD
    # How long it may take to establish a TCP connection
    SOCKET_TIMEOUT = 3600
    # How long it may take to get the output of our agent
    # (including tunefs'ing N devices)
    SSH_READ_TIMEOUT = 3600

    args = {"hostname": ssh_monitor.host.address,
            "username": ssh_monitor.get_username(),
            "timeout": SOCKET_TIMEOUT}
    if ssh_monitor.port:
        args["port"] = ssh_monitor.port
    # Note: paramiko has a hardcoded 15 second timeout on SSH handshake after
    # successful TCP connection (Transport.banner_timeout).
    ssh.connect(**args)
    transport = ssh.get_transport()
    channel = transport.open_session()
    channel.settimeout(SSH_READ_TIMEOUT)
    channel.exec_command(command)
    result_stdout = channel.makefile('rb').read()
    result_stderr = channel.makefile_stderr('rb').read()
    result_code = channel.recv_exit_status()
    ssh.close()

    print result_code, command
    if result_code != 0:
        print result_stdout
        print result_stderr
    return result_code, result_stdout, result_stderr

class StateChangeJob:
    def get_state_info(self):
        """Return a 3 tuple of class, old state, new state"""
        raise NotImplementedError

class FormatTargetJob(Job, StateChangeJob):
    def __init__(self, target):
        steps = [(MkfsStep, {'target_id': target.id})]
        super(FormatTargetJob, self).__init__(steps)

class SetupFilesystemJob(Job):
    def __init__(self, filesystem):
        mgs = filesystem.mgs
        mdt = MetadataTarget.objects.get(filesystem = filesystem)
        ost_list = ObjectStoreTarget.objects.filter(filesystem = filesystem)

        steps = [
                (MkfsStep, {'target_id': mgs.id}),
                (MkfsStep, {'target_id': mdt.id}),
                ]
        steps.extend([(MkfsStep, {'target_id': ost.id}) for ost in ost_list])

        steps.append((MountStep, {'target_mount_id': mgs.targetmount_set.get(primary = True).id}))
        steps.append((MountStep, {'target_mount_id': mdt.targetmount_set.get(primary = True).id}))
        steps.extend([(MountStep, {'target_mount_id': ost.targetmount_set.get(primary = True).id}) for ost in ost_list])

        print steps

        super(SetupFilesystemJob, self).__init__(steps)

class StartFilesystemJob(Job):
    def __init__(self, filesystem):
        mgs = filesystem.mgs
        mdt = MetadataTarget.objects.get(filesystem = filesystem)
        ost_list = ObjectStoreTarget.objects.filter(filesystem = filesystem)

        steps = []
        steps.append((MountStep, {'target_mount_id': mgs.targetmount_set.get(primary = True).id}))
        steps.append((MountStep, {'target_mount_id': mdt.targetmount_set.get(primary = True).id}))
        steps.extend([(MountStep, {'target_mount_id': ost.targetmount_set.get(primary = True).id}) for ost in ost_list])

        super(StartFilesystemJob, self).__init__(steps)

class StopFilesystemJob(Job):
    def __init__(self, filesystem):
        mgs = filesystem.mgs
        mdt = MetadataTarget.objects.get(filesystem = filesystem)
        ost_list = ObjectStoreTarget.objects.filter(filesystem = filesystem)
        steps = []

        steps.append((UnmountStep, {'target_mount_id': mgs.targetmount_set.get(primary = True).id}))
        steps.append((UnmountStep, {'target_mount_id': mdt.targetmount_set.get(primary = True).id}))
        steps.extend([(UnmountStep, {'target_mount_id': ost.targetmount_set.get(primary = True).id}) for ost in ost_list])

        super(StopFilesystemJob, self).__init__(steps)

from monitor.models import *
from configure.models import *

class MkfsStep(Step):
    def _mkfs_command(self, target):
        args = []
        primary_mount = target.targetmount_set.get(primary = True)

        args.append({
            ManagedMgs: "--mgs",
            ManagedMdt: "--mdt",
            ManagedOst: "--ost"
            }[target.__class__])

        if isinstance(target, FilesystemMember):
            args.append("--fsname=%s" % target.filesystem.name)
            args.extend(target.mgsnode_spec())

        args.append("--reformat")

        for secondary_mount in target.targetmount_set.filter(primary = False):
            host = secondary_mount.host
            nids = ",".join([n.nid_string for n in host.nid_set.all()])
            assert(nids != "")
            args.append("--failover=%s" % nids)

        args.append(primary_mount.block_device.path)

        return "/usr/sbin/mkfs.lustre %s" % " ".join(args)

    def run(self, kwargs):
        target_id = kwargs['target_id']
        target = Target.objects.get(id = target_id).downcast()

        assert(isinstance(target, ConfiguredTarget))
        host = target.targetmount_set.get(primary = True).host
        command = self._mkfs_command(target)

        code, out, err = debug_ssh(host, command)
        # Assume nonzero returns from mkfs mean it didn't touch anything
        if code != 0:
            from configure.lib.job import StepDirtyError
            raise StepDirtyError()

class MountStep(Step):
    def _mount_command(self, target_mount):
        return "mount -t lustre %s %s" % (target_mount.block_device.path, target_mount.mount_point)

    def is_idempotent(self):
        return True

    def run(self, kwargs):
        target_mount_id = kwargs['target_mount_id']
        target_mount = TargetMount.objects.get(id = target_mount_id)

        code, out, err = debug_ssh(target_mount.host, self._mount_command(target_mount))
        if code != 0 and code != 17 and code != 114:
            from configure.lib.job import StepCleanError
            print code, out, err
            print StepCleanError
            raise StepCleanError()

class UnmountStep(Step):
    def _unmount_command(self, target_mount):
        return "umount -t lustre %s" % (target_mount.mount_point)

    def is_idempotent(self):
        return True

    def run(self, kwargs):
        target_mount_id = kwargs['target_mount_id']
        target_mount = TargetMount.objects.get(id = target_mount_id)

        code, out, err = debug_ssh(target_mount.host, self._unmount_command(target_mount))
        # FIXME: assuming code=1 is an 'already unmounted' therefore ok
        if (code != 0) and (code != 1):
            from configure.lib.job import StepCleanError
            print code, out, err
            print StepCleanError
            raise StepCleanError()

@task()
def run_job_step(step_instance):
    try:
        step_instance.wrap_run()
    except StepPaused:
        # TODO: deal with multiple jobs in the queue at the same time: there are
        # ways that this could get the steps mixed up
        self.retry(step_instance, countdown = STEP_PAUSE_DELAY)


