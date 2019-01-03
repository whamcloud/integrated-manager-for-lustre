#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================

import json
import mock

from chroma_core.lib.util import chroma_settings
from iml_common.lib.name_value_list import NameValueList


def patch_test_host_contact_task(context, result_attrs={}):
    from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient

    status = NameValueList(
        [
            {"resolve": True},
            {"ping": True},
            {"auth": True},
            {"hostname_valid": True},
            {"fqdn_resolves": True},
            {"fqdn_matches": True},
            {"reverse_resolve": True},
            {"reverse_ping": True},
            {"yum_valid_repos": True},
            {"yum_can_update": True},
            {"openssl": True},
        ]
    )

    status.add(result_attrs)

    # Don't overwrite the original reference!
    if not "old_test_host_contact" in context:
        context.old_test_host_contact = JobSchedulerClient.test_host_contact

    def mock_test_host_contact(address, root_pw, pkey, pkey_pw):
        from chroma_core.models import StepResult, TestHostConnectionJob, Command, TestHostConnectionStep

        command = Command.objects.create(message="Mock Test Host Contact", complete=True)
        job = TestHostConnectionJob.objects.create(
            state="complete", address=address, root_pw=None, pkey=None, pkey_pw=None
        )
        command.jobs.add(job)
        StepResult.objects.create(
            job=job,
            backtrace="an error",
            step_klass=TestHostConnectionStep,
            args={"address": address, "credentials_key": 1},
            step_index=0,
            step_count=1,
            state="complete",
            result=json.dumps({"address": address, "status": status.collection(), "valid": True}),
        )

        return command

    JobSchedulerClient.test_host_contact = mock.Mock(side_effect=mock_test_host_contact)


def before_all(context):
    settings = chroma_settings()
    from django.core.management import setup_environ

    setup_environ(settings)

    ### Take a TestRunner hostage.
    # Use django_nose's runner so that we can take advantage of REUSE_DB=1.
    from django_nose import NoseTestSuiteRunner

    # We'll use these later to frog-march Django through the motions
    # of setting up and tearing down the test environment, including
    # test databases.
    context.runner = NoseTestSuiteRunner()

    ## If you use South for migrations, uncomment this to monkeypatch
    ## syncdb to get migrations to run.
    from south.management.commands import patch_for_test_db_setup

    patch_for_test_db_setup()


def before_feature(context, feature):
    context.runner.setup_test_environment()
    context.old_db_config = context.runner.setup_databases()

    from tests.unit.services.job_scheduler.job_test_case import JobTestCase

    class BehaveFeatureTest(JobTestCase):
        mock_servers = {}

        def runTest(self):
            pass

    context.test_case = BehaveFeatureTest()
    context.test_case._pre_setup()
    context.test_case.setUp()

    patch_test_host_contact_task(context)

    from tests.unit.chroma_core.helpers import synthetic_host
    from tests.unit.chroma_core.helpers import freshen
    from chroma_core.lib.cache import ObjectCache
    from chroma_core.models import ManagedHost, Command
    from chroma_core.services.job_scheduler.agent_rpc import AgentRpc

    def create_host_ssh(address, server_profile, root_pw, pkey, pkey_pw):
        host_data = AgentRpc.mock_servers[address]
        host = synthetic_host(address, nids=host_data["nids"], fqdn=host_data["fqdn"], nodename=host_data["nodename"])
        ObjectCache.add(ManagedHost, host)
        command = Command.objects.create(complete=True, message="Mock create_host_ssh")
        return host, command

    from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient

    context.old_create_host_ssh = JobSchedulerClient.create_host_ssh
    JobSchedulerClient.create_host_ssh = mock.Mock(side_effect=create_host_ssh)

    context.old_create_targets = JobSchedulerClient.create_targets

    def create_targets(*args, **kwargs):
        targets, command = context.old_create_targets(*args, **kwargs)
        context.test_case.drain_progress()
        return [freshen(t) for t in targets], freshen(command)

    JobSchedulerClient.create_targets = mock.Mock(side_effect=create_targets)

    context.old_create_filesystem = JobSchedulerClient.create_filesystem

    def create_filesystem(*args, **kwargs):
        filesystem_id, command_id = context.old_create_filesystem(*args, **kwargs)
        context.test_case.drain_progress()
        return filesystem_id, command_id

    JobSchedulerClient.create_filesystem = mock.Mock(side_effect=create_filesystem)

    context.old_set_state = Command.set_state

    def set_state(objects, message=None, **kwargs):
        command = context.old_set_state(objects, message=message, **kwargs)
        context.test_case.drain_progress()
        if command:
            return freshen(command)
        else:
            return command

    Command.set_state = mock.Mock(side_effect=set_state)

    context.old_run_jobs = JobSchedulerClient.command_run_jobs

    def command_run_jobs(jobs, message):
        command_id = context.old_run_jobs(jobs, message)
        context.test_case.drain_progress()
        return command_id

    JobSchedulerClient.command_run_jobs = mock.Mock(side_effect=command_run_jobs)

    from chroma_cli.api import ApiHandle

    context.old_api_client = ApiHandle.ApiClient
    from tests.unit.chroma_api.tastypie_test import TestApiClient

    ApiHandle.ApiClient = TestApiClient

    from chroma_api.authentication import CsrfAuthentication

    context.old_is_authenticated = CsrfAuthentication.is_authenticated
    CsrfAuthentication.is_authenticated = mock.Mock(return_value=True)

    from tests.unit.chroma_core.helpers import load_default_profile
    from chroma_core.models import ServerProfile

    if not ServerProfile.objects.all().exists():
        load_default_profile()


def after_feature(context, feature):
    context.test_case.tearDown()

    from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
    from chroma_core.models import Command

    JobSchedulerClient.create_host_ssh = context.old_create_host_ssh
    JobSchedulerClient.create_targets = context.old_create_targets
    JobSchedulerClient.create_filesystem = context.old_create_filesystem
    JobSchedulerClient.command_run_jobs = context.old_run_jobs
    Command.set_state = context.old_set_state

    # If one of the steps fails, an exception will be thrown and the
    # transaction rolled back.  In which case, this teardown will cause
    # a TME which we don't care about.
    from django.db.transaction import TransactionManagementError as TME

    try:
        context.test_case._post_teardown()
    except TME:
        pass

    context.runner.teardown_databases(context.old_db_config)
    context.runner.teardown_test_environment()

    # As of Django 1.4, teardown_databases() no longer restores the
    # original db name in the connection's settings dict.  The reasoning
    # is documented in https://code.djangoproject.com/ticket/10868, and
    # their concerns are understandable.  In our case, however, we're not
    # going on to do anything here which might affect the production DB.
    # Therefore, the following hack restores pre-1.4 behavior:
    for connection, old_name, destroy in context.old_db_config[0]:
        connection.settings_dict["NAME"] = old_name

    from chroma_cli.api import ApiHandle

    ApiHandle.ApiClient = context.old_api_client

    from chroma_api.authentication import CsrfAuthentication

    CsrfAuthentication.is_authenticated = context.old_is_authenticated

    from django.contrib.contenttypes.models import ContentType

    ContentType.objects.clear_cache()

    from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient

    JobSchedulerClient.test_host_contact = context.old_test_host_contact


##--def before_scenario(context, scenario):
# --    # Set up the scenario test environment
# --    context.runner.setup_test_environment()
# --    # We must set up and tear down the entire database between
# --    # scenarios. We can't just use db transactions, as Django's
# --    # TestClient does, if we're doing full-stack tests with Mechanize,
# --    # because Django closes the db connection after finishing the HTTP
# --    # response.
# --    context.old_db_config = context.runner.setup_databases()


# --def after_scenario(context, scenario):
# --    # Tear down the scenario test environment.
# --    context.runner.teardown_databases(context.old_db_config)
# --    context.runner.teardown_test_environment()
# --    # Bob's your uncle.


def before_scenario(context, scenario):
    context.cli_failure_expected = False
