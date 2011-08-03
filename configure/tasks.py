
from celery.decorators import task

from configure.lib.job import Job, Step, StepPaused, STEP_PAUSE_DELAY
from configure.models import *

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

state_change_job_classes = []
class StateChangeJob:
    def __init__(self, stateful_object):
        assert(isinstance(stateful_object, StatefulObject))
        self.stateful_object = stateful_object

    class __metaclass__(type):
        def __init__(cls, name, bases, dict):
            type.__init__(cls, name, bases, dict)
            if Job in bases:
                state_change_job_classes.append(cls)

class DependencyAbsent(Exception):
    """A Job wants to depend on something that doesn't exist"""
    pass

class RegisterTargetJob(Job, StateChangeJob):
    # FIXME: this really isn't ManagedTarget, it's FilesystemMember+ManagedTarget
    state_transition = (ManagedTarget, 'formatted', 'registered')
    def __init__(self, target):
        # FIXME: somehow need to avoid advertising this transition for MGS targets
        assert(isinstance(target, FilesystemMember))

        self.target = target
        steps = [(MountStep, {"target_mount_id": target.target_mount_set.get(primary = True)})]
        super(RegisterTargetJob, self).__init__(steps)
        StateChangeJob.__init__(self, target)

    def get_deps(self):
        deps = []
        # TODO: depend on MDT state registered if this is OST
        if isinstance(self, ObjectStoreTarget):
            try:
                mdt = MetadataTarget.objects.get(filesystem = self.target.filesystem)
            except MetadataTarget.DoesNotExist:
                raise DependencyAbsent("Cannot register OSTs for filesystem %s until an MDT is created" % self.target.filesystem)
            deps.append((mdt, "registered"))

        mgs = self.target.filesystem.mgs
        deps.append((mgs.targetmount_set.get(primary = True), "mounted"))

class StartTargetMountJob(Job, StateChangeJob):
    state_transition = (ManagedTargetMount, 'unmounted', 'mounted')
    def __init__(self, target_mount):
        self.target_mount = target_mount
        steps = [(MountStep, {"target_mount_id": target_mount.id})]
        super(StartTargetMountJob, self).__init__(steps)
        StateChangeJob.__init__(self, target_mount)

    def get_deps(self):
        pass

class StopTargetMountJob(Job, StateChangeJob):
    state_transition = (ManagedTargetMount, 'mounted', 'unmounted')
    def __init__(self, target_mount):
        steps = [(UnmountStep, {"target_mount_id": target_mount.id})]
        super(StopTargetMountJob, self).__init__(steps)
        StateChangeJob.__init__(self, target_mount)

class FormatTargetJob(Job, StateChangeJob):
    state_transition = (ManagedTarget, 'unformatted', 'formatted')
    def __init__(self, target):
        steps = [(MkfsStep, {'target_id': target.id})]
        super(FormatTargetJob, self).__init__(steps)
        StateChangeJob.__init__(self, target)

class LoadLNetJob(Job, StateChangeJob):
    state_transition = (ManagedHost, 'lnet_unloaded', 'lnet_down')
    def __init__(self, host):
        self.host = host
        steps = [(LoadLNetStep, {'host_id': host.id})]
        super(LoadLNetJob, self).__init__(steps)
        StateChangeJob.__init__(self, host)

class UnloadLNetJob(Job, StateChangeJob):
    state_transition = (ManagedHost, 'lnet_down', 'lnet_unloaded')
    def __init__(self, host):
        self.host = host
        steps = [(UnloadLNetStep, {'host_id': host.id})]
        super(UnloadLNetJob, self).__init__(steps)
        StateChangeJob.__init__(self, host)
    
class StartLNetJob(Job, StateChangeJob):
    state_transition = (ManagedHost, 'lnet_down', 'lnet_up')
    def __init__(self, host):
        self.host = host
        steps = [(StartLNetStep, {'host_id': host.id})]
        super(StartLNetJob, self).__init__(steps)
        StateChangeJob.__init__(self, host)

class StopLNetJob(Job, StateChangeJob):
    state_transition = (ManagedHost, 'lnet_up', 'lnet_down')
    def __init__(self, host):
        self.host = host
        steps = [(StopLNetStep, {'host_id': host.id})]
        super(StopLNetJob, self).__init__(steps)
        StateChangeJob.__init__(self, host)

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

        #steps.append((MountStep, {'target_mount_id': mgs.targetmount_set.get(primary = True).id}))
        #steps.append((MountStep, {'target_mount_id': mdt.targetmount_set.get(primary = True).id}))
        #steps.extend([(MountStep, {'target_mount_id': ost.targetmount_set.get(primary = True).id}) for ost in ost_list])

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
            assert nids != "", RuntimeError("No NIDs known for host %s" % host)
            args.append("--failover=%s" % nids)

        args.append(primary_mount.block_device.path)

        return "/usr/sbin/mkfs.lustre %s" % " ".join(args)

    def run(self, kwargs):
        target_id = kwargs['target_id']
        target = Target.objects.get(id = target_id).downcast()

        assert(isinstance(target, ManagedTarget))
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

class StartLNetStep(Step):
    def is_idempotent(self):
        return True

    def run(self, kwargs):
        host = Host.objects.get(id = kwargs['host_id'])

        code, out, err = debug_ssh(host, "/usr/sbin/lctl network up")
        if code != 0:
            from configure.lib.job import StepCleanError
            print code, out, err
            print StepCleanError
            raise StepCleanError()

class StopLNetStep(Step):
    def is_idempotent(self):
        return True

    def run(self, kwargs):
        host = Host.objects.get(id = kwargs['host_id'])

        code, out, err = debug_ssh(host, "/root/hydra-rmmod.py ptlrpc; /usr/sbin/lctl network down")
        if code != 0:
            from configure.lib.job import StepCleanError
            print code, out, err
            print StepCleanError
            raise StepCleanError()


class LoadLNetStep(Step):
    def is_idempotent(self):
        return True

    def run(self, kwargs):
        host = Host.objects.get(id = kwargs['host_id'])

        code, out, err = debug_ssh(host, "/sbin/modprobe lnet")
        if code != 0:
            from configure.lib.job import StepCleanError
            print code, out, err
            print StepCleanError
            raise StepCleanError()

class UnloadLNetStep(Step):
    def is_idempotent(self):
        return True

    def run(self, kwargs):
        host = Host.objects.get(id = kwargs['host_id'])

        code, out, err = debug_ssh(host, "/root/hydra-rmmod.py lnet")
        if code != 0:
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


