
import datetime
import subprocess
import tempfile
import uuid
from dateutil import tz
import mock

from chroma_core.models import LogMessage
from chroma_core.models import Bundle, Command, ServerProfile
from chroma_core.lib.cache import ObjectCache
from chroma_core.services.job_scheduler.job_scheduler import JobScheduler
from chroma_core.services.log import log_register

log = log_register('test_helper')


def random_str(length=10, prefix='', postfix=''):

    test_string = (str(uuid.uuid4()).translate(None, '-'))[:length]

    return "%s%s%s" % (prefix, test_string, postfix)


def synchronous_run_job(job):
    for step_klass, args in job.get_steps():
        step_klass(job, args, lambda x: None, lambda x: None, mock.Mock()).run(args)


def _passthrough_create_targets(target_data):
    ObjectCache.clear()
    return JobScheduler().create_targets(target_data)
create_targets_patch = mock.patch("chroma_core.services.job_scheduler.job_scheduler_client.JobSchedulerRpc.create_targets",
                                 new = mock.Mock(side_effect = _passthrough_create_targets), create = True)


def _passthrough_create_filesystem(target_data):
    ObjectCache.clear()
    return JobScheduler().create_filesystem(target_data)
create_filesystem_patch = mock.patch("chroma_core.services.job_scheduler.job_scheduler_client.JobSchedulerRpc.create_filesystem",
                                     new = mock.Mock(side_effect = _passthrough_create_filesystem), create = True)


def freshen(obj):
    return obj.__class__.objects.get(pk=obj.pk)


def generate_csr(common_name):
    # Generate a disposable CSR
    client_key = tempfile.NamedTemporaryFile(delete = False)
    subprocess.call(['openssl', 'genrsa', '-out', client_key.name, '2048'], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    csr = subprocess.Popen(['openssl', "req", "-new", "-subj", "/C=/ST=/L=/O=/CN=%s" % common_name, "-key", client_key.name],
                           stdout = subprocess.PIPE, stderr = subprocess.PIPE).communicate()[0]
    return csr


def fake_log_message(message):
    t = datetime.datetime.utcnow()
    t = t.replace(tzinfo = tz.tzutc())
    return LogMessage.objects.create(
        datetime = t,
        message = message,
        severity = 0,
        facility = 0,
        tag = "",
        message_class = LogMessage.get_message_class(message)
    )


def load_default_bundles():
    Bundle.objects.create(bundle_name='lustre', location='/tmp/',
                          description='Lustre Bundle')
    Bundle.objects.create(bundle_name='agent', location='/tmp/',
                          description='Agent Bundle')
    Bundle.objects.create(bundle_name='agent_dependencies', location='/tmp/',
                          description='Agent Dependency Bundle')


def load_default_profile():
    load_default_bundles()
    default_sp = ServerProfile(name='test_profile', ui_name='Managed storage server',
                               ui_description='A storage server suitable for creating new HA-enabled filesystem targets',
                               managed=True, default=True,
                               initial_state="managed")
    default_sp.bundles.add('lustre')
    default_sp.bundles.add('agent')
    default_sp.bundles.add('agent_dependencies')
    default_sp.save()


def make_command(dismissed=False, complete=False, created_at=None, failed=True, message='test'):

    command = Command.objects.create(dismissed=dismissed,
        message=message,
        complete=complete,
        errored=failed)

    #  Command.created_at is auto_add_now - so have to update it
    if created_at is not None:
        command.created_at = created_at
        command.save()
        command = freshen(command)

    return command
