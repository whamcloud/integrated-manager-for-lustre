#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================
from chroma_core.lib.util import chroma_settings


class FakeTestHostContactTask(object):
    def __init__(self, resolve=True, ping=True, agent=True,
                 reverse_resolve=True, reverse_ping=True):
        self.resolve = resolve
        self.ping = ping
        self.agent = agent
        self.reverse_resolve = reverse_resolve
        self.reverse_ping = reverse_ping

    def delay(self, host):
        result = {
            'address': host.address,
            'resolve': self.resolve,
            'ping': self.ping,
            'agent': self.agent,
            'reverse_resolve': self.reverse_resolve,
            'reverse_ping': self.reverse_ping,
        }

        from celery.states import SUCCESS
        from celery.result import EagerResult
        return EagerResult(42, result, SUCCESS)


def patch_test_host_contact_task(context, fake_task=None):
    if not fake_task:
        fake_task = FakeTestHostContactTask()

    import chroma_core.tasks
    # Don't overwrite the original reference!
    if not 'old_test_host_contact' in context:
        context.old_test_host_contact = chroma_core.tasks.test_host_contact
    chroma_core.tasks.test_host_contact = fake_task


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
    context.cli_failure_expected = False

    from tests.unit.chroma_core.helper import JobTestCase

    class BehaveFeatureTest(JobTestCase):
        mock_servers = {}

        def runTest(self):
            pass

    context.test_case = BehaveFeatureTest()
    context.test_case._pre_setup()
    context.test_case.setUp()

    patch_test_host_contact_task(context)

    from chroma_cli.api import ApiHandle
    context.old_api_client = ApiHandle.ApiClient
    from tests.unit.chroma_api.tastypie_test import TestApiClient
    ApiHandle.ApiClient = TestApiClient

    from chroma_api.authentication import CsrfAuthentication
    context.old_is_authenticated = CsrfAuthentication.is_authenticated
    import mock
    CsrfAuthentication.is_authenticated = mock.Mock(return_value = True)


def after_feature(context, feature):
    context.test_case.tearDown()

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
        connection.settings_dict['NAME'] = old_name

    from chroma_cli.api import ApiHandle
    ApiHandle.ApiClient = context.old_api_client

    from chroma_api.authentication import CsrfAuthentication
    CsrfAuthentication.is_authenticated = context.old_is_authenticated

    import chroma_core.tasks
    chroma_core.tasks.test_host_contact = context.old_test_host_contact
#--def before_scenario(context, scenario):
#--    # Set up the scenario test environment
#--    context.runner.setup_test_environment()
#--    # We must set up and tear down the entire database between
#--    # scenarios. We can't just use db transactions, as Django's
#--    # TestClient does, if we're doing full-stack tests with Mechanize,
#--    # because Django closes the db connection after finishing the HTTP
#--    # response.
#--    context.old_db_config = context.runner.setup_databases()


#--def after_scenario(context, scenario):
#--    # Tear down the scenario test environment.
#--    context.runner.teardown_databases(context.old_db_config)
#--    context.runner.teardown_test_environment()
#--    # Bob's your uncle.
