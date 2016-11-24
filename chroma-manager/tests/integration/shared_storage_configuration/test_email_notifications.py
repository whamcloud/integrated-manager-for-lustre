from testconfig import config
from django.utils.unittest import skipIf
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


@skipIf(config.get('simulator'), 'RealRemoteOperations simulator cant fake out ssh')
class TestEmailNotifications(ChromaIntegrationTestCase):
    SETTINGS_DIR = '/usr/share/chroma-manager'

    def setUp(self):
        super(TestEmailNotifications, self).setUp()
        self.manager = config['chroma_managers'][0]
        self.remote_operations.make_directory(self.manager['fqdn'], '%s/messages' % self.SETTINGS_DIR)
        file_content = """EMAIL_BACKEND = \'django.core.mail.backends.filebased.EmailBackend\'\nEMAIL_FILE_PATH = \'/usr/share/chroma-manager/messages\'\nEMAIL_HOST = \'localhost\'"""
        self.remote_operations.create_file(self.manager['fqdn'], file_content,
                                           '%s/local_settings.py' % self.SETTINGS_DIR)
        self.restart_chroma_manager(self.manager['fqdn'])

    def tearDown(self):
        self.remote_operations.delete_file(self.manager['fqdn'], '%s/local_settings.py*' % self.SETTINGS_DIR)
        self.remote_operations.delete_file(self.manager['fqdn'], '%s/messages' % self.SETTINGS_DIR)
        self.restart_chroma_manager(self.manager['fqdn'])
        super(TestEmailNotifications, self).tearDown()

    def test_email_notifications(self):
        self.assertEqual(len(self.remote_operations.list_dir(self.manager['fqdn'], '%s/messages' % self.SETTINGS_DIR)),
                         0)

        user = self.chroma_manager.get('/api/session/').json['user']
        alert_types = self.chroma_manager.get('api/alert_type/').json['objects']
        pacemaker_alert = [alert for alert in alert_types if alert['description'] == 'Pacemaker stopped alert']

        self.chroma_manager.post('api/alert_subscription/', body={
            'alert_type': pacemaker_alert[0]['resource_uri'],
            'user': user['resource_uri']
        })

        host = self.add_hosts([config['lustre_servers'][0]['address']], high_availability=True)[0]
        self.remote_operations.stop_pacemaker(host['address'])

        dir_list = self.remote_operations.list_dir(self.manager['fqdn'], '%s/messages' % self.SETTINGS_DIR)
        self.assertEqual(len(dir_list), 1)

        message = self.remote_operations.read_file(self.manager['fqdn'],
                                                   '%s/messages/%s' % (self.SETTINGS_DIR, dir_list[0]))
        self.assertTrue("Pacemaker stopped" in message)
