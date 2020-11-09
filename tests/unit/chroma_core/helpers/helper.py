import subprocess
import tempfile
import uuid
import mock

from chroma_core.models import LogMessage
from chroma_core.models import ServerProfile
from chroma_core.lib.cache import ObjectCache
from chroma_core.services.job_scheduler.job_scheduler import JobScheduler
from chroma_core.services.log import log_register
from iml_common.lib.date_time import IMLDateTime

log = log_register("test_helper")


def random_str(length=10, prefix="", postfix=""):

    test_string = (str(uuid.uuid4()).translate(None, "-"))[:length]

    return "%s%s%s" % (prefix, test_string, postfix)


def synchronous_run_job(job):
    for step_klass, args in job.get_steps():
        step_klass(job, args, lambda x: None, lambda x: None, mock.Mock()).run(args)


def _passthrough_create_targets(target_data):
    ObjectCache.clear()
    return JobScheduler().create_targets(target_data)


create_targets_patch = mock.patch(
    "chroma_core.services.job_scheduler.job_scheduler_client.JobSchedulerRpc.create_targets",
    new=mock.Mock(side_effect=_passthrough_create_targets),
    create=True,
)


def _passthrough_create_filesystem(target_data):
    ObjectCache.clear()
    return JobScheduler().create_filesystem(target_data)


create_filesystem_patch = mock.patch(
    "chroma_core.services.job_scheduler.job_scheduler_client.JobSchedulerRpc.create_filesystem",
    new=mock.Mock(side_effect=_passthrough_create_filesystem),
    create=True,
)


def freshen(obj):
    return obj.__class__.objects.get(pk=obj.pk)


def generate_csr(common_name):
    # Generate a disposable CSR
    client_key = tempfile.NamedTemporaryFile(delete=False)
    subprocess.call(
        ["openssl", "genrsa", "-out", client_key.name, "2048"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    csr = subprocess.Popen(
        ["openssl", "req", "-new", "-sha256", "-subj", "/C=/ST=/L=/O=/CN=%s" % common_name, "-key", client_key.name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).communicate()[0]

    return csr


def fake_log_message(message):
    return LogMessage.objects.create(
        datetime=IMLDateTime.utcnow(),
        message=message,
        severity=0,
        facility=0,
        tag="",
        message_class=LogMessage.get_message_class(message),
    )


def load_default_profile():
    default_sp = ServerProfile(
        name="test_profile",
        ui_name="Managed storage server",
        ui_description="A storage server suitable for creating new HA-enabled filesystem targets",
        managed=True,
        default=True,
        corosync=True,
        corosync2=False,
        ntp=True,
        initial_state="managed",
    )
    default_sp.save()
