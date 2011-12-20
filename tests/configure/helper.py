
from django.test import TestCase


class MockAgent(object):
    label_counter = 0
    mock_servers = {}

    succeed = True

    def __init__(self, host, log = None, console_callback = None, timeout = None):
        self.host = host

    def invoke(self, cmdline, args = None):
        if not self.succeed:
            raise RuntimeError("Test-generated failure")

        print "invoke_agent %s %s %s" % (self.host, cmdline, args)
        if cmdline == "get-fqdn":
            return self.mock_servers[self.host.address]['fqdn']
        elif cmdline == "lnet-scan":
            return self.mock_servers[self.host.address]['nids']
        elif cmdline.startswith("format-target"):
            import uuid
            return {'uuid': uuid.uuid1().__str__()}
        elif cmdline.startswith('start-target'):
            # FIXME: this will be nodename when HYD-455 is done
            return {'location': self.host.fqdn}
        elif cmdline.startswith('register-target'):
            MockAgent.label_counter += 1
            return {'label': "foofs-TTT%04d" % self.label_counter}


class JobTestCase(TestCase):
    def _test_lun(self, host):
        from configure.models import Lun, LunNode
        lun = Lun.objects.create(shareable = False)
        LunNode.objects.create(lun = lun, host = host, path = "/fake/path/%s" % lun.id, primary = True)
        return lun

    def setUp(self):
        # FIXME: have to do this before every test because otherwise
        # one test will get all the setup of StoragePluginClass records,
        # the in-memory instance of storage_plugin_manager will expect
        # them to still be there but they'll have been cleaned
        # out of the database.  Setting up this stuff should be done
        # as part of the initial DB setup before any test is started
        # so that it's part of the baseline that's rolled back to
        # after each test.
        import configure.lib.storage_plugin.manager
        configure.lib.storage_plugin.manager.storage_plugin_manager = configure.lib.storage_plugin.manager.StoragePluginManager()

        # NB by this stage celery has already read in its settings, so we have to update
        # ALWAYS_EAGER inside celery instead of in settings.*
        from celery.app import app_or_default
        self.old_celery_always_eager = app_or_default().conf.CELERY_ALWAYS_EAGER
        app_or_default().conf.CELERY_ALWAYS_EAGER = True
        self.old_celery_eager_propagates_exceptions = app_or_default().conf.CELERY_EAGER_PROPAGATES_EXCEPTIONS
        app_or_default().conf.CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

        # Intercept attempts to call out to lustre servers
        import configure.lib.agent
        self.old_agent = configure.lib.agent.Agent
        MockAgent.mock_servers = self.mock_servers
        configure.lib.agent.Agent = MockAgent

    def tearDown(self):
        import configure.lib.agent
        configure.lib.agent.Agent = self.old_agent

        from celery.app import app_or_default
        app_or_default().conf.CELERY_ALWAYS_EAGER = self.old_celery_always_eager
        app_or_default().conf.CELERY_ALWAYS_EAGER = self.old_celery_eager_propagates_exceptions
