#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


def before_all(context):
    from chroma_core.lib.chroma_settings import chroma_settings
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

    from tests.unit.chroma_core.helper import JobTestCase

    class BehaveFeatureTest(JobTestCase):
        mock_servers = {}

        def runTest(self):
            pass

    context.test_case = BehaveFeatureTest()
    context.test_case._pre_setup()
    context.test_case.setUp()

    from chroma_cli.api import ApiHandle
    context.old_api_client = ApiHandle.ApiClient
    from tests.unit.chroma_api.tastypie_test import TestApiClient
    ApiHandle.ApiClient = TestApiClient


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

    from chroma_cli.api import ApiHandle
    ApiHandle.ApiClient = context.old_api_client

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
