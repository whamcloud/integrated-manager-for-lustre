from datetime import timedelta
import logging
from django.utils import timezone

from chroma_core.models import Command, Event, HostOfflineAlert

from tests.unit.chroma_api.notification_test_case import NotificationTestCase
from tests.unit.chroma_core.helper import synthetic_host

log = logging.getLogger(__name__)


class TestNotification(NotificationTestCase):

    def test_get_all_default_fields(self):
        """Given notifications of each type, issue a GET request, and check response has all notifications"""

        host = synthetic_host()
        host.state = 'lnet_up'
        host.save()

        alert_begin = timezone.now()
        alert_obj = self.make_host_notification(HostOfflineAlert,
                                                host=host,
                                                date=alert_begin,
                                                failed=False,
                                                severity=logging.INFO,
                                                dismissed=True)

        event_created = timezone.now() - timedelta(days=1)
        event_obj = self.make_host_notification(Event,
                                                host=host,
                                                date=event_created,
                                                failed=False,
                                                severity=logging.WARNING,
                                                dismissed=True)
        command_created = timezone.now() - timedelta(days=1)
        command_obj = self.make_host_notification(Command,
                                                  host=host,
                                                  date=command_created,
                                                  failed=False,
                                                  dismissed=False)

        response = self.api_client.get("/api/notification/")
        self.assertHttpOK(response)
        notifications = self.deserialize(response)['objects']

        types_returned = [n['type'] for n in notifications]
        self.assertTrue('AlertState' in types_returned)
        self.assertTrue('Event' in types_returned)
        self.assertTrue('Command' in types_returned)

        subtypes_returned = [n['subtype'] for n in notifications]
        self.assertTrue('HostOfflineAlert' in subtypes_returned)
        self.assertTrue('SyslogEvent' in subtypes_returned)

        messages_returned = [n['message'] for n in notifications]
        self.assertTrue(alert_obj.message() in messages_returned, messages_returned)
        self.assertTrue(event_obj.message() in messages_returned, messages_returned)
        self.assertTrue(command_obj.message in messages_returned, messages_returned)

        severities_returned = [n['severity'] for n in notifications if n['severity'] is not None]
        self.assertEqual(len(severities_returned), 3)
        self.assertTrue('INFO' in severities_returned)
        self.assertTrue('WARNING' in severities_returned)
        self.assertTrue('ERROR' not in severities_returned)

        self.assertTrue(len([True for n in notifications if n['dismissed']]), 2)
        self.assertTrue(len([True for n in notifications if not n['dismissed']]), 1)

        created_at_returned = [n['created_at'] for n in notifications]
        self.assertEqual(len(created_at_returned), 3)

    def test_get_commands_severity(self):
        """Commands do not have a severity attribute, so test that errored=True is ERROR, and errored=False is INFO"""

        # Create 2 Command records in the DB - one errored one not
        self.make_host_notification(Command, failed=False, message='not_errored')
        self.make_host_notification(Command, failed=True, message='errored')

        response = self.api_client.get("/api/notification/")
        self.assertHttpOK(response)
        notifications = self.deserialize(response)['objects']

        self.assertEqual(len(notifications), 2)
        for notification in notifications:
            if notification['message'] == 'not_errored':
                self.assertEqual('INFO', notification['severity'])
            elif notification['message'] == 'errored':
                self.assertEqual('ERROR', notification['severity'])
            else:
                self.fail("unexpected alert: %s" % notification['message'])
