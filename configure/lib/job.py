
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from logging import getLogger, FileHandler, StreamHandler, DEBUG, INFO
import settings
import time

job_log = getLogger('job')
job_log.setLevel(DEBUG)
job_log.addHandler(FileHandler(settings.JOB_LOG_PATH))
if settings.DEBUG:
    job_log.setLevel(DEBUG)
    job_log.addHandler(StreamHandler())
else:
    job_log.setLevel(INFO)

class StepPaused(Exception):
    """A step did not execute because the job is paused."""
    pass

class StepAborted(Exception):
    """A step did not execute because the job has errored."""
    pass

class StepFailed(Exception):
    """A step executed and returned an exception.  The job has been marked as errored."""
    def __init__(self, step_exception):
        self.step_exception = step_exception
    pass

class StepCleanError(Exception):
    """A step encountered an error which prevented it making any changes,
       such the step may be retried at will.  For example, an attempt to
       mkfs over ssh failed to establish a connection: there is no risk that
       mkfs command started running"""
    pass

class StepDirtyError(Exception):
    """A step encountered an error which may have left the system in 
       an inconsistent state.  For example, connectivity was lost partway
       through a mkfs operation: we don't know if the filesystem is formatted
       or not"""
    pass


STEP_PAUSE_DELAY = 10

class Step(object):
    def __init__(self, job, args):
        self.args = args
        self.job_id = job.id

        # This step is the final one in the job
        self.final = False

    def mark_final(self):
        self.final = True

    def is_idempotent(self):
        """Indicate whether the step is idempotent.  For example, mounting 
           a target.  Step subclasses which are idempotent should override this and
           return True."""
        return False

    def run(self):
        raise NotImplementedError

    def retry(self):
        steps = self.get_steps()
        # Which one failed?

class StateChangeJob(object):
    """Subclasses must define a class attribute 'stateful_object'
       identifying another attribute which returns a StatefulObject"""

    # Tuple of (StatefulObjectSubclass, old_state, new_state)
    state_transition = None
    # Name of an attribute which is a ForeignKey to a StatefulObject
    stateful_object = None
    # Terse human readable verb, e.g. "Change this" (for buttons)
    state_verb = None

    def get_stateful_object(self):
        from configure.models import StatefulObject
        stateful_object = getattr(self, self.stateful_object)
        assert(isinstance(stateful_object, StatefulObject))
        return stateful_object

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

    job_log.debug("debug_ssh:%s:%s:%s" % (host, result_code, command))
    if result_code != 0:
        job_log.error("debug_ssh:%s:%s:%s" % (host, result_code, command))
        job_log.error(result_stdout)
        job_log.error(result_stderr)
    return result_code, result_stdout, result_stderr


class MkfsStep(Step):
    def _mkfs_command(self, target):
        from hydra_agent.cmds import lustre
        from monitor.models import FilesystemMember
        from configure.models import ManagedMgs, ManagedMdt, ManagedOst
        kwargs = {}
        primary_mount = target.targetmount_set.get(primary = True)

        kwargs['target_types'] = {
            ManagedMgs: "mgs",
            ManagedMdt: "mdt",
            ManagedOst: "ost"
            }[target.__class__]

        if isinstance(target, FilesystemMember):
            kwargs['fsname'] = target.filesystem.name
            kwargs['mgsnode'] = target.filesystem.mgs_nids()

        kwargs['reformat'] = True

        for secondary_mount in target.targetmount_set.filter(primary = False):
            host = secondary_mount.host
            nids = [n.nid_string for n in host.nid_set.all()]
            if len(nids) > 0:
                kwargs['failnode'] = nids

        kwargs['device'] = primary_mount.block_device.path

        return lustre.mkfs(**kwargs)

    def run(self, kwargs):
        from monitor.models import Target
        from configure.models import ManagedTarget
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

class NullStep(Step):
    def run(self, kwargs):
        pass

class MountStep(Step):
    def is_idempotent(self):
        return True

    def run(self, kwargs):
        from monitor.models import TargetMount
        target_mount_id = kwargs['target_mount_id']
        target_mount = TargetMount.objects.get(id = target_mount_id)

        code, out, err = debug_ssh(target_mount.host,
                                   "hydra-agent.py --start_target %s" %
                                   target_mount.target.name)
        if code != 0 and code != 17 and code != 114:
            from configure.lib.job import StepCleanError
            print code, out, err
            print StepCleanError
            raise StepCleanError()

class RegisterTargetStep(Step):
    def is_idempotent(self):
        return True

    def run(self, kwargs):
        from monitor.models import TargetMount
        target_mount_id = kwargs['target_mount_id']
        target_mount = TargetMount.objects.get(id = target_mount_id)

        code, out, err = debug_ssh(target_mount.host,
                                   "hydra-agent.py --register_target %s %s" %
                                   (target_mount.block_device.path,
                                    target_mount.mount_point))
        if code != 0:
            from configure.lib.job import StepCleanError
            print code, out, err
            print StepCleanError
            raise StepCleanError()
        else:
            data = json.loads(out)
            target = target_mount.target
            target.name = data['label']
            target.save()

class ConfigurePacemakerStep(Step):
    def is_idempotent(self):
        return True

    def run(self, kwargs):
        from monitor.models import TargetMount
        target_mount_id = kwargs['target_mount_id']
        target_mount = TargetMount.objects.get(id = target_mount_id)
        # due to devices where it's not entirely obvious that sharing is
        # going on, it takes an audit cycle to find a shared device after
        # it's been registered.  we need to wait for that audit cycle.
        x = 0
        while (target_mount.block_device == None or
               target_mount.target.name == None) and x < 10:
            print "waiting for the target's name"
            time.sleep(10)
            target_mount = TargetMount.objects.get(id = target_mount_id)
            x = x + 1
        if target_mount.block_device == None or target_mount.target.name == None:
            from configure.lib.job import StepCleanError
            print "failed to get the target's name after %d tries" % x
            print StepCleanError
            raise StepCleanError()

        code, out, err = debug_ssh(target_mount.host,
                                   "hydra-agent.py --configure_ha %s %s %s %s" %
                                   (target_mount.block_device.path,
                                    target_mount.target.name,
                                    target_mount.primary,
                                    target_mount.mount_point))
        if code != 0:
            from configure.lib.job import StepCleanError
            print code, out, err
            print StepCleanError
            raise StepCleanError()

class StartLNetStep(Step):
    def is_idempotent(self):
        return True

    def run(self, kwargs):
        from hydra_agent.cmds import lustre
        from monitor.models import Host
        host = Host.objects.get(id = kwargs['host_id'])

        code, out, err = debug_ssh(host, lustre.lnet_start())
        if code != 0:
            from configure.lib.job import StepCleanError
            print code, out, err
            print StepCleanError
            raise StepCleanError()

class StopLNetStep(Step):
    def is_idempotent(self):
        return True

    def run(self, kwargs):
        from hydra_agent.cmds import lustre
        from monitor.models import Host
        host = Host.objects.get(id = kwargs['host_id'])

        code, out, err = debug_ssh(host, lustre.lnet_stop())
        if code != 0:
            from configure.lib.job import StepCleanError
            print code, out, err
            print StepCleanError
            raise StepCleanError()

class LoadLNetStep(Step):
    def is_idempotent(self):
        return True

    def run(self, kwargs):
        from hydra_agent.cmds import lustre
        from monitor.models import Host
        host = Host.objects.get(id = kwargs['host_id'])

        code, out, err = debug_ssh(host, lustre.lnet_load())
        if code != 0:
            from configure.lib.job import StepCleanError
            print code, out, err
            print StepCleanError
            raise StepCleanError()

class UnloadLNetStep(Step):
    def is_idempotent(self):
        return True

    def run(self, kwargs):
        from monitor.models import Host
        host = Host.objects.get(id = kwargs['host_id'])

        code, out, err = debug_ssh(host, lustre.lnet_unload())
        if code != 0:
            from configure.lib.job import StepCleanError
            print code, out, err
            print StepCleanError
            raise StepCleanError()

class UnmountStep(Step):
    def _unmount_command(self, target_mount):
        from hydra_agent.cmds import lustre
        return lustre.umount(dir=target_mount.mount_point)

    def is_idempotent(self):
        return True

    def run(self, kwargs):
        from monitor.models import TargetMount
        target_mount_id = kwargs['target_mount_id']
        target_mount = TargetMount.objects.get(id = target_mount_id)

        code, out, err = debug_ssh(target_mount.host, self._unmount_command(target_mount))
        # FIXME: assuming code=1 is an 'already unmounted' therefore ok
        if (code != 0) and (code != 1):
            from configure.lib.job import StepCleanError
            print code, out, err
            print StepCleanError
            raise StepCleanError()

class ConfParamStep(Step):
    def is_idempotent(self):
        return False

    def run(self, kwargs):
        from configure.models import ConfParam
        conf_param = ConfParam.objects.get(pk = kwargs['conf_param_id']).downcast()

        if conf_param.value:
            lctl_command = "lctl conf_param %s=%s" % (conf_param.get_key(), conf_param.value)
        else:
            lctl_command = "lctl conf_param -d %s" % conf_param.get_key()
        code, out, err = debug_ssh(conf_param.mgs.primary_server(), lctl_command)
        if (code != 0):
            from configure.lib.job import StepCleanError
            job_log.error(code, out, err)
            raise StepDirtyError()

class ConfParamVersionStep(Step):
    def is_idempotent(self):
        return True

    def run(self, kwargs):
        from configure.models import ManagedMgs
        ManagedMgs.objects.\
            filter(pk = kwargs['mgs_id']).\
            update(conf_param_version_applied = kwargs['version'])
