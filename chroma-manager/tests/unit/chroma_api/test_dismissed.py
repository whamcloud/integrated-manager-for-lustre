import logging
from datetime import timedelta
from dateutil.parser import parse

from django.utils import timezone

from chroma_core.models import (Command, ManagedHost, Event, HostOfflineAlert)

from tests.unit.chroma_api.notification_test_case import NotificationTestCase
from tests.unit.chroma_core.helper import freshen, synthetic_host

INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR


class TestInitialLoadDismissables(NotificationTestCase):
    """Test initial load of data

    Any unread events, alerts or commands in the system should be returned
    time is not a factor on initial loads.

    Sending all fields as strings to simulate what I think the FE will do
    """

    def setUp(self):
        super(TestInitialLoadDismissables, self).setUp()

        #  Make one of each kinds of dismissable object
        for dismissed in [True, False]:
            for level in [INFO, WARNING, ERROR]:
                self.make_host_notification(HostOfflineAlert, dismissed=dismissed,
                                      severity=level, date=timezone.now())
                self.make_host_notification(Event, dismissed=dismissed,
                                      severity=level)
            for failed in [True, False]:
                self.make_host_notification(Command, dismissed=dismissed,
                                      failed=failed)

    def test_fetch_not_dismissed_events(self):
        data = {"dismissed": 'false',
                "severity__in": ['WARNING', 'ERROR']}

        response = self.api_client.get("/api/event/", data = data)

        self.assertHttpOK(response)
        objects = self.deserialize(response)['objects']
        self.assertEqual(len(objects), 2, self.dump_objects(objects))
        for ev in objects:
            self.assertEqual(ev['dismissed'], False)
            self.assertTrue(ev['severity'] in ['WARNING', 'ERROR'])

    def test_fetch_not_dismissed_alerts(self):
        data = {"dismissed": 'false',
                "severity__in": ['WARNING', 'ERROR']}

        response = self.api_client.get("/api/alert/", data=data)

        self.assertHttpOK(response)
        objects = self.deserialize(response)['objects']
        self.assertEqual(len(objects), 2, self.dump_objects(objects))
        for ev in objects:
            self.assertEqual(ev['dismissed'], False)
            self.assertTrue(ev['severity'] in ['WARNING', 'ERROR'])

    def test_fetch_not_dismissed_commands(self):
        data = {"dismissed": 'false',
                "errored": 'true'}

        response = self.api_client.get("/api/command/", data=data)

        self.assertHttpOK(response)
        objects = self.deserialize(response)['objects']
        self.assertEqual(len(objects), 1, self.dump_objects(objects))
        for ev in objects:
            self.assertEqual(ev['dismissed'], False)


class TestSubsequentLoadDismissables(NotificationTestCase):
    """After the first load the UI can request updates based on date

    Sending all fields as strings to simulate what I think the FE does
    """

    def setUp(self):
        super(TestSubsequentLoadDismissables, self).setUp()

        self.sample_date = timezone.now() - timedelta(seconds=120)
        previous_sample = self.sample_date - timedelta(seconds=180)
        current_sample = self.sample_date + timedelta(seconds=60)

        #  Make one of each kinds of dismissable object with dates
        for dismissed in [True, False]:
            for level in [INFO, WARNING, ERROR]:
                for date in [previous_sample, current_sample]:
                    self.make_host_notification(HostOfflineAlert, dismissed=dismissed,
                                          severity=level, date=date)
                    self.make_host_notification(Event, dismissed=dismissed,
                                          severity=level, date=date)
            for failed in [True, False]:
                self.make_host_notification(Command, dismissed=dismissed,
                                      failed=failed)

    def test_fetch_not_dismissed_events_since_last_sample(self):

        data = {"created_at__gte": str(self.sample_date),
                "dismissed": 'false',
                "severity__in": ['WARNING', 'ERROR']}

        response = self.api_client.get("/api/event/", data=data)
        self.assertHttpOK(response)
        objects = self.deserialize(response)['objects']
        self.assertEqual(len(objects), 2, self.dump_objects(objects))
        for ev in objects:
            self.assertEqual(ev['dismissed'], False)
            self.assertTrue(ev['severity'] in ['WARNING', 'ERROR'])
            self.assertTrue(parse(ev['created_at']) >= self.sample_date)

    def test_fetch_not_dismissed_alerts_since_last_sample(self):

        data = {"begin__gte": str(self.sample_date),
                "dismissed": 'false',
                "severity__in": ['WARNING', 'ERROR']}

        response = self.api_client.get("/api/alert/", data=data)
        self.assertHttpOK(response)
        objects = self.deserialize(response)['objects']
        self.assertEqual(len(objects), 2, self.dump_objects(objects))
        for ev in objects:
            self.assertEqual(ev['dismissed'], False)
            self.assertTrue(ev['severity'] in ['WARNING', 'ERROR'])
            self.assertTrue(parse(ev['begin']) >= self.sample_date)

    def test_fetch_not_dismissed_commands_since_last_sample(self):

        data = {"created_at__gte": str(self.sample_date),
                "dismissed": 'false',
                "errored": 'true'}

        response = self.api_client.get("/api/command/", data=data)
        self.assertHttpOK(response)
        objects = self.deserialize(response)['objects']
        self.assertEqual(len(objects), 1, self.dump_objects(objects))
        for ev in objects:
            self.assertEqual(ev['dismissed'], False)
            self.assertTrue(parse(ev['created_at']) >= self.sample_date)


class TestPatchDismissables(NotificationTestCase):
    """After the first load the UI can request updates based on date

    Sending all fields as strings to simulate what I think the FE does
    """
    def test_dismissing_alert(self):
        """Send a API PATCH to update Alert.dismissed to True"""

        alert = self.make_host_notification(HostOfflineAlert, dismissed=False,
            severity=WARNING, date=timezone.now())
        self.assertEqual(alert.dismissed, False)

        path = '/api/alert/%s/' % alert.pk
        # reject if severity isn't descriptive string as per the api
        response = self.api_client.patch(path, data={'dismissed': True, 'severity': 10})
        self.assertHttpBadRequest(response)
        response = self.api_client.patch(path, data={'dismissed': True})
        self.assertHttpAccepted(response)

        alert = freshen(alert)
        self.assertEqual(alert.dismissed, True)

    def test_dismissing_command(self):
        """Send a API PATCH to update Command.dismissed to True"""

        command = self.make_host_notification(Command, dismissed=False, failed=True)
        self.assertEqual(command.dismissed, False)

        data = {"dismissed": 'true'}
        response = self.api_client.patch("/api/command/%s/" % command.pk,
            data=data)
        self.assertHttpAccepted(response)

        command = freshen(command)
        self.assertEqual(command.dismissed, True)

    def test_dismissing_event(self):
        """Send a API PATCH to update Event.dismissed to True"""

        event = self.make_host_notification(Event, dismissed=False, severity=WARNING)
        self.assertEqual(event.dismissed, False)

        data = {"dismissed": 'true'}
        response = self.api_client.patch("/api/event/%s/" % event.pk,
            data=data)
        self.assertHttpAccepted(response)

        event = freshen(event)
        self.assertEqual(event.dismissed, True)


class TestPatchDismissablesWithDeletedRelatedObject(NotificationTestCase):
    """After the first load the UI can request updates based on date

    Sending all fields as strings to simulate what I think the FE does
    """
    def test_dismissing_alert(self):
        """Send a API PATCH to update Alert.dismissed to True with del obj

        HostOfflineAlert.alert_item is a GenericForeignKey.  This will test that
        item being set, but deleted
        """

        alert = self.make_host_notification(HostOfflineAlert, dismissed=False,
            severity=WARNING, date=timezone.now())
        self.assertEqual(alert.dismissed, False)

        self.assertEqual(type(alert.alert_item), ManagedHost)
        alert.alert_item.mark_deleted()

        #  Make sure it is deleted.
        self.assertRaises(ManagedHost.DoesNotExist,
                          ManagedHost.objects.get,
                          pk=alert.alert_item.pk)

        #  Should not be able to PATCH this to dismissed without a failure
        data = {"dismissed": 'true'}
        response = self.api_client.patch("/api/alert/%s/" % alert.pk, data=data)
        self.assertHttpAccepted(response)

        alert = freshen(alert)
        self.assertEqual(alert.dismissed, True)

    def test_dismissing_event(self):
        """Send a API PATCH to update Event.dismissed to True"""

        host = synthetic_host()
        event = self.make_host_notification(Event, host=host, dismissed=False, severity=WARNING)
        self.assertEqual(event.dismissed, False)

        event.host.mark_deleted()

        #  Make sure it is deleted.
        self.assertRaises(ManagedHost.DoesNotExist,
                          ManagedHost.objects.get,
                          pk=event.host.pk)

        data = {"dismissed": 'true'}
        response = self.api_client.patch("/api/event/%s/" % event.pk,
            data=data)
        self.assertHttpAccepted(response)

        event = freshen(event)
        self.assertEqual(event.dismissed, True)


class TestNotLoggedInUsersCannotDismiss(NotificationTestCase):
    """Make sure non-logged in users cannot Dismiss or Dismiss all alerts

    This test characterizes a bug in django-tastypie v0.9.11.
    See HYD-2339 for details.

    When we decided to update tastypie, we can disable
    the fix for this, and run this test to too verify is unnecessary.
    See HYD-2354
    """

    def test_dismissing_alert(self):
        """Test dismissing alert, not logged in is prevented"""

        alert = self.make_host_notification(HostOfflineAlert, dismissed=False,
            severity=WARNING, date=timezone.now())
        self.assertEqual(alert.dismissed, False)

        self.api_client.client.logout()

        # ensure logged off
        self.assertFalse(self.api_client.client.session)

        data = {"dismissed": 'true'}
        response = self.api_client.patch("/api/alert/%s/" % alert.pk, data=data)
        self.assertHttpUnauthorized(response)

        alert = freshen(alert)
        self.assertEqual(alert.dismissed, False)

    def test_dismissing_command(self):
        """Test dismissing command, not logged in is prevented"""

        command = self.make_host_notification(Command, dismissed=False, failed=True)
        self.assertEqual(command.dismissed, False)

        self.api_client.client.logout()

        # ensure logged off
        self.assertFalse(self.api_client.client.session)

        data = {"dismissed": 'true'}
        response = self.api_client.patch("/api/command/%s/" % command.pk,
            data=data)
        self.assertHttpUnauthorized(response)

        command = freshen(command)
        self.assertEqual(command.dismissed, False)

    def test_dismissing_event(self):
        """Test dismissing event, not logged in is prevented"""

        event = self.make_host_notification(Event, dismissed=False, severity=WARNING)
        self.assertEqual(event.dismissed, False)

        self.api_client.client.logout()

        # ensure logged off
        self.assertFalse(self.api_client.client.session)

        data = {"dismissed": 'true'}
        response = self.api_client.patch("/api/event/%s/" % event.pk,
            data=data)
        self.assertHttpUnauthorized(response)

        event = freshen(event)
        self.assertEqual(event.dismissed, False)


class TestFSAdminsCanDismiss(NotificationTestCase):
    """Make sure filesystem_administrators can Dismiss or Dismiss all alerts

    Bug HYD-2619
    """

    def __init__(self, methodName=None):
        super(TestFSAdminsCanDismiss, self).__init__(
            methodName, username='admin', password='chr0m4_d3bug')

    def test_dismissing_alert(self):
        """Test dismissing alert by fs admins is allowed"""

        alert = self.make_host_notification(HostOfflineAlert, dismissed=False,
            severity=WARNING, date=timezone.now())
        self.assertEqual(alert.dismissed, False)

        data = {"dismissed": 'true'}
        response = self.api_client.patch("/api/alert/%s/" % alert.pk, data=data)
        self.assertHttpAccepted(response)

        alert = freshen(alert)
        self.assertEqual(alert.dismissed, True)

    def test_dismissing_command(self):
        """Test dismissing command by fs admins is allowed"""

        command = self.make_host_notification(Command, dismissed=False, failed=True)
        self.assertEqual(command.dismissed, False)

        data = {"dismissed": 'true'}
        response = self.api_client.patch("/api/command/%s/" % command.pk,
            data=data)
        self.assertHttpAccepted(response)

        command = freshen(command)
        self.assertEqual(command.dismissed, True)

    def test_dismissing_event(self):
        """Test dismissing event by fs admins is allowed"""

        event = self.make_host_notification(Event, dismissed=False, severity=WARNING)
        self.assertEqual(event.dismissed, False)

        data = {"dismissed": 'true'}
        response = self.api_client.patch("/api/event/%s/" % event.pk,
            data=data)
        self.assertHttpAccepted(response)

        event = freshen(event)
        self.assertEqual(event.dismissed, True)


class TestFSUsersCannotDismiss(NotificationTestCase):
    """Make sure filesystem_users cannot Dismiss or Dismiss all alerts

    This test characterizes a bug in django-tastypie v0.9.11.
    See HYD-2339 for details.

    When we decided to update tastypie, we can disable
    the fix for this, and run this test to too verify is unnecessary.
    See HYD-2354
    """

    def __init__(self, methodName=None):
        super(TestFSUsersCannotDismiss, self).__init__(
            methodName, username='user', password='chr0m4_d3bug')

    def test_dismissing_alert(self):
        """Test dismissing alert by fs users is prevented"""

        alert = self.make_host_notification(HostOfflineAlert, dismissed=False,
            severity=WARNING, date=timezone.now())
        self.assertEqual(alert.dismissed, False)

        data = {"dismissed": 'true'}
        response = self.api_client.patch("/api/alert/%s/" % alert.pk, data=data)
        self.assertHttpUnauthorized(response)

        alert = freshen(alert)
        self.assertEqual(alert.dismissed, False)

    def test_dismissing_command(self):
        """Test dismissing command by fs users is prevented"""

        command = self.make_host_notification(Command, dismissed=False, failed=True)
        self.assertEqual(command.dismissed, False)

        data = {"dismissed": 'true'}
        response = self.api_client.patch("/api/command/%s/" % command.pk,
            data=data)
        self.assertHttpUnauthorized(response)

        command = freshen(command)
        self.assertEqual(command.dismissed, False)

    def test_dismissing_event(self):
        """Test dismissing event by fs users is prevented"""

        event = self.make_host_notification(Event, dismissed=False, severity=WARNING)
        self.assertEqual(event.dismissed, False)

        data = {"dismissed": 'true'}
        response = self.api_client.patch("/api/event/%s/" % event.pk,
            data=data)
        self.assertHttpUnauthorized(response)

        event = freshen(event)
        self.assertEqual(event.dismissed, False)
