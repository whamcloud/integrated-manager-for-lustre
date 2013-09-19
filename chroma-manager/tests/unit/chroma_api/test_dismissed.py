from datetime import timedelta
import logging
import uuid
from dateutil.parser import parse

from django.utils import timezone

from chroma_core.models import (Command, HostOfflineAlert, ManagedHost,
                                Event, AlertState)
from chroma_core.models.event import SyslogEvent

from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase
from tests.unit.chroma_api.tastypie_test import ResourceTestCase
from tests.unit.chroma_core.helper import freshen

INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR


class DismissableTestSupport():
    """TestCase to hold state constructors, and helper methods """

    def make_dismissable(self, obj_type, dismissed=False, severity=INFO,
                         date=None, failed=None):
        """Create one of 3 types of objects that can be dismissed by a user"""

        if obj_type == AlertState:
            return self.make_alertstate(dismissed=dismissed, severity=severity,
                                 created_at=date)
        elif obj_type == Event:
            return self.make_event(dismissed=dismissed, severity=severity,
                            created_at=date)
        elif obj_type == Command:
            return self.make_command(dismissed=dismissed, created_at=date,
                              failed=failed)

    def make_event(self, host=None, dismissed=False,
                   severity=INFO, created_at=None):

        event = SyslogEvent.objects.create(severity=severity,
                                          dismissed=dismissed,
                                          message_str='test')

        if host is not None:
            event.host = host

        #  Event.created_at is auto_add_now - so have to update it
        if created_at is not None:
            event.created_at = created_at

        event.save()
        event = freshen(event)

        return event

    def make_command(self, dismissed=False, created_at=None, failed=True):

        command = Command.objects.create(dismissed=dismissed,
                                         message='test',
                                         errored=failed)

        #  Command.created_at is auto_add_now - so have to update it
        if created_at is not None:
            command.created_at = created_at
            command.save()
            command = freshen(command)

        return command

    def make_alertstate(self, alert_item=None, dismissed=False, severity=INFO,
                        created_at=None, active=False):

        if alert_item is None:
            alert_item = self.make_random_managed_host()

        alert_type = alert_item.__class__.__name__

        # The following fields must be unique together for each AlertState
        # alert_item_type, alert_item_id, alert_type, active
        # item_type and item_id are the content_type and pk of alert_item
        return HostOfflineAlert.objects.create(severity=severity,
                                               active=active,
                                               alert_item=alert_item,
                                               begin=created_at,
                                               end=created_at,
                                               dismissed=dismissed,
                                               alert_type=alert_type)

    def make_random_managed_host(self):
        """Create and save a managed host with a somewhat random address

        ManagedHost requires that address is unique, so to create more then
        one per test, random ones are created.
        """

        address = self.random_str(postfix=".tld")
        nodename = 'node-name'
        self.host = ManagedHost.objects.create(
            address=address,
            fqdn="%s.%s" % (nodename, address),
            nodename=nodename)

        return self.host

    def random_str(self, length=10, prefix='', postfix=''):

        test_string = (str(uuid.uuid4()).translate(None, '-'))[:length]

        return "%s%s%s" % (prefix, test_string, postfix)

    def dump_objects(self, objects):
        return "\n" + "\n\n".join([repr(o) for o in objects])


class TestInitialLoadDismissables(ChromaApiTestCase, DismissableTestSupport):
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
                self.make_dismissable(AlertState, dismissed=dismissed,
                                      severity=level, date=timezone.now())
                self.make_dismissable(Event, dismissed=dismissed,
                                      severity=level)
            for failed in [True, False]:
                self.make_dismissable(Command, dismissed=dismissed,
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


class TestSubsequentLoadDismissables(ChromaApiTestCase, DismissableTestSupport):
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
                    self.make_dismissable(AlertState, dismissed=dismissed,
                                          severity=level, date=date)
                    self.make_dismissable(Event, dismissed=dismissed,
                                          severity=level, date=date)
            for failed in [True, False]:
                self.make_dismissable(Command, dismissed=dismissed,
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


class TestPatchDismissables(ChromaApiTestCase, DismissableTestSupport):
    """After the first load the UI can request updates based on date

    Sending all fields as strings to simulate what I think the FE does
    """
    def test_dismissing_alert(self):
        """Send a API PATCH to update Alert.dismissed to True"""

        alert = self.make_dismissable(AlertState, dismissed=False,
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

        command = self.make_dismissable(Command, dismissed=False, failed=True)
        self.assertEqual(command.dismissed, False)

        data = {"dismissed": 'true'}
        response = self.api_client.patch("/api/command/%s/" % command.pk,
            data=data)
        self.assertHttpAccepted(response)

        command = freshen(command)
        self.assertEqual(command.dismissed, True)

    def test_dismissing_event(self):
        """Send a API PATCH to update Event.dismissed to True"""

        event = self.make_dismissable(Event, dismissed=False, severity=WARNING)
        self.assertEqual(event.dismissed, False)

        data = {"dismissed": 'true'}
        response = self.api_client.patch("/api/event/%s/" % event.pk,
            data=data)
        self.assertHttpAccepted(response)

        event = freshen(event)
        self.assertEqual(event.dismissed, True)


class TestPatchDismissablesWithDeletedRelatedObject(ChromaApiTestCase, DismissableTestSupport):
    """After the first load the UI can request updates based on date

    Sending all fields as strings to simulate what I think the FE does
    """
    def test_dismissing_alert(self):
        """Send a API PATCH to update Alert.dismissed to True with del obj

        AlertState.alert_item is a GenericForeignKey.  This will test that
        item being set, but deleted
        """

        alert = self.make_dismissable(AlertState, dismissed=False,
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

        event = self.make_event(self.make_random_managed_host(),
                                dismissed=False, severity=WARNING)
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


class TestNotLoggedInUsersCannotDismiss(ResourceTestCase, DismissableTestSupport):
    """Make sure non-logged in users cannot Dismiss or Dismiss all alerts

    This test characterizes a bug in django-tastypie v0.9.11.
    See HYD-2339 for details.

    When we decided to update tastypie, we can disable
    the fix for this, and run this test to too verify is unnecessary.
    See HYD-2354
    """

    def test_dismissing_alert(self):
        """Test dismissing alert, not logged in is prevented"""

        alert = self.make_dismissable(AlertState, dismissed=False,
            severity=WARNING, date=timezone.now())
        self.assertEqual(alert.dismissed, False)

        # ensure logged off
        self.assertFalse(self.api_client.client.session)

        data = {"dismissed": 'true'}
        response = self.api_client.patch("/api/alert/%s/" % alert.pk, data=data)
        self.assertHttpUnauthorized(response)

        alert = freshen(alert)
        self.assertEqual(alert.dismissed, False)

    def test_dismissing_command(self):
        """Test dismissing command, not logged in is prevented"""

        command = self.make_dismissable(Command, dismissed=False, failed=True)
        self.assertEqual(command.dismissed, False)

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

        event = self.make_dismissable(Event, dismissed=False, severity=WARNING)
        self.assertEqual(event.dismissed, False)

        # ensure logged off
        self.assertFalse(self.api_client.client.session)

        data = {"dismissed": 'true'}
        response = self.api_client.patch("/api/event/%s/" % event.pk,
            data=data)
        self.assertHttpUnauthorized(response)

        event = freshen(event)
        self.assertEqual(event.dismissed, False)


class TestFSUsersCannotDismiss(ChromaApiTestCase, DismissableTestSupport):
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

        alert = self.make_dismissable(AlertState, dismissed=False,
            severity=WARNING, date=timezone.now())
        self.assertEqual(alert.dismissed, False)

        data = {"dismissed": 'true'}
        response = self.api_client.patch("/api/alert/%s/" % alert.pk, data=data)
        self.assertHttpUnauthorized(response)

        alert = freshen(alert)
        self.assertEqual(alert.dismissed, False)

    def test_dismissing_command(self):
        """Test dismissing command by fs users is prevented"""

        command = self.make_dismissable(Command, dismissed=False, failed=True)
        self.assertEqual(command.dismissed, False)

        data = {"dismissed": 'true'}
        response = self.api_client.patch("/api/command/%s/" % command.pk,
            data=data)
        self.assertHttpUnauthorized(response)

        command = freshen(command)
        self.assertEqual(command.dismissed, False)

    def test_dismissing_event(self):
        """Test dismissing event by fs users is prevented"""

        event = self.make_dismissable(Event, dismissed=False, severity=WARNING)
        self.assertEqual(event.dismissed, False)

        data = {"dismissed": 'true'}
        response = self.api_client.patch("/api/event/%s/" % event.pk,
            data=data)
        self.assertHttpUnauthorized(response)

        event = freshen(event)
        self.assertEqual(event.dismissed, False)
