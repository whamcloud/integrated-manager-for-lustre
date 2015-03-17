from datetime import timedelta

import logging
from django.utils import timezone

from chroma_core.models import Command, Event, HostOfflineAlert, AlertState

from tests.unit.chroma_api.notification_test_case import NotificationTestCase
from tests.unit.chroma_core.helper import synthetic_host

log = logging.getLogger(__name__)


class TestNotification(NotificationTestCase):

    NOTIFICATION_TYPES = 3

    def test_get_all_default_fields(self):
        """Given notifications of each type, issue a GET request, and check response has all notifications"""

        host = synthetic_host()
        host.state = 'managed'
        host.save()

        alert_obj = self.make_host_notification(HostOfflineAlert,
                                                host=host,
                                                date=timezone.now(),
                                                failed=False,
                                                severity=logging.INFO,
                                                dismissed=True)

        event_obj = self.make_host_notification(Event,
                                                host=host,
                                                date=timezone.now() - timedelta(days=1),
                                                failed=False,
                                                severity=logging.WARNING,
                                                dismissed=True)

        command_obj = self.make_host_notification(Command,
                                                  host=host,
                                                  date=timezone.now() - timedelta(days=1),
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

    def _create_notifications(self, clear, test_notifications, dismissed, command_complete):
        if clear:
            # Start from scratch.
            AlertState.objects.all().delete()
            Event.objects.all().delete()
            Command.objects.all().delete()

        response = self.api_client.get("/api/notification/", data = {'limit': 0})
        self.assertHttpOK(response)
        start_notifications = len(self.deserialize(response)['objects'])

        for create in range(test_notifications / self.NOTIFICATION_TYPES):
            host = synthetic_host()
            host.save()

            self.make_host_notification(HostOfflineAlert,
                                        host=host,
                                        date=timezone.now(),
                                        failed=False,
                                        severity=logging.INFO,
                                        dismissed=dismissed)

            self.make_host_notification(Event,
                                        host=host,
                                        date=timezone.now(),
                                        failed=False,
                                        severity=logging.WARNING,
                                        dismissed=dismissed)

            self.make_host_notification(Command,
                                        host=host,
                                        date=timezone.now(),
                                        failed=False,
                                        complete=command_complete,
                                        dismissed=dismissed)

        response = self.api_client.get("/api/notification/", data = {'limit': 0})
        self.assertHttpOK(response)
        notifications = self.deserialize(response)['objects']

        self.assertTrue(len(notifications) == (start_notifications + test_notifications))

    def test_dismiss_all(self):
        """
        Create a lot of notifications and then dismiss them, ensure the dismiss is a minimal number of queries.
        """
        test_notifications = 30                # I'd like to do thousands but the test just becomes too slow.

        # Just check that when we dismiss all the notifications they all disappear. The commands will disappear
        # because command.complete will be true.
        self._create_notifications(True, test_notifications, False, True)

        # The tastypie transaction does a couple of queries then we get 3 updates one for each type of Notification.
        with self.assertQueries('SELECT', 'SELECT', 'UPDATE', 'UPDATE', 'UPDATE'):
            response = self.api_client.put("/api/notification/dismiss_all/")
            self.assertHttpAccepted(response)

        for dismissed in [True, False]:
            response = self.api_client.get("/api/notification/", data = {'limit': 0, 'dismissed': dismissed})
            self.assertHttpOK(response)
            notifications = self.deserialize(response)['objects']

            self.assertTrue(len(notifications) == (test_notifications if dismissed else 0))

        # Delete them a type at a time.
        # The commands will disappear because command.complete will be true.
        self._create_notifications(True, test_notifications, False, True)

        for partial in ["command", "alert", "event"]:
            # The tastypie transaction does a couple of queries then we get 1 update
            with self.assertQueries('SELECT', 'SELECT', 'UPDATE'):
                response = self.api_client.put("/api/%s/dismiss_all/" % partial)
                self.assertHttpAccepted(response)

            response = self.api_client.get("/api/%s/" % partial, data = {'limit': 0, 'dismissed': False})
            self.assertHttpOK(response)
            notifications = self.deserialize(response)['objects']

            self.assertTrue(len(notifications) == 0)

        response = self.api_client.get("/api/notification/", data = {'limit': 0, 'dismissed': False})
        self.assertHttpOK(response)
        notifications = self.deserialize(response)['objects']

        self.assertTrue(len(notifications) == 0)

        # Check the commands.complete = False do not disappear.
        self._create_notifications(True, test_notifications, False, False)

        # The tastypie transaction does a couple of queries then we get 3 updates one for each type of Notification.
        with self.assertQueries('SELECT', 'SELECT', 'UPDATE', 'UPDATE', 'UPDATE'):
            response = self.api_client.put("/api/notification/dismiss_all/")
            self.assertHttpAccepted(response)

        response = self.api_client.get("/api/notification/", data = {'limit': 0, 'dismissed': False})
        self.assertHttpOK(response)
        notifications = self.deserialize(response)['objects']

        # The commands should be left because commands.complete was False
        self.assertTrue(len(notifications) == test_notifications / self.NOTIFICATION_TYPES)

    def test_select_notifications(self):
        """
        Create a lot of notifications and then dismiss them, ensure the dismiss is a minimal number of queries.
        """
        test_notifications = 30                # I'd like to do thousands but the test just becomes too slow.

        # Create dismissed and not dismissed notifications..
        self._create_notifications(True, test_notifications, False, True)
        self._create_notifications(False, test_notifications, True, True)

        # This loop first runs a simple query that the optimized routine will deal with, then adds created_at <
        # which will cause the tasypie routines to activate. This checks both work appropriately.
        # The 3rd loop adds another parameter that means no results should be returned
        data = {}

        for loop in range(3):
            for dismissed in [True, False]:
                for limit in range(test_notifications - 10, test_notifications + 11, 10):
                    expected = min(test_notifications, limit) if loop < 2 else 0

                    data['limit'] = limit
                    data['dismissed'] = dismissed

                    response = self.api_client.get("/api/notification/", data = data)
                    self.assertHttpOK(response)
                    notifications = self.deserialize(response)['objects']

                    self.assertTrue(len(notifications) == expected)

            data['created_at__lt'] = timezone.now()

            if loop == 1:
                data['created_at__gt'] = data['created_at__lt']
