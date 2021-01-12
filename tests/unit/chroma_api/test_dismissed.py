import logging
from datetime import timedelta

from django.utils import timezone
from chroma_core.models import ManagedHost
from chroma_core.models import HostOfflineAlert
from tests.unit.chroma_api.notification_test_case import NotificationTestCase
from tests.unit.chroma_core.helpers.helper import freshen
from emf_common.lib.date_time import EMFDateTime

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
                self.make_alertstate(HostOfflineAlert, dismissed=dismissed, severity=level, created_at=timezone.now())

    def test_fetch_not_dismissed_alerts(self):
        data = {"dismissed": False, "severity__in": ["WARNING", "ERROR"]}

        response = self.api_client.get("/api/alert/", data=data)

        self.assertHttpOK(response)
        objects = self.deserialize(response)["objects"]
        self.assertEqual(len(objects), 2, self.dump_objects(objects))
        for ev in objects:
            self.assertEqual(ev["dismissed"], False)
            self.assertTrue(ev["severity"] in ["WARNING", "ERROR"])


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
                    self.make_alertstate(HostOfflineAlert, dismissed=dismissed, severity=level, created_at=date)

    def test_fetch_not_dismissed_alerts_since_last_sample(self):

        data = {"begin__gte": str(self.sample_date), "dismissed": False, "severity__in": ["WARNING", "ERROR"]}

        response = self.api_client.get("/api/alert/", data=data)
        self.assertHttpOK(response)
        objects = self.deserialize(response)["objects"]
        self.assertEqual(len(objects), 2, self.dump_objects(objects))
        for ev in objects:
            self.assertEqual(ev["dismissed"], False)
            self.assertTrue(ev["severity"] in ["WARNING", "ERROR"])
            self.assertTrue(EMFDateTime.parse(ev["begin"]) >= self.sample_date)


class TestPatchDismissables(NotificationTestCase):
    """After the first load the UI can request updates based on date

    Sending all fields as strings to simulate what I think the FE does
    """

    def test_dismissing_alert(self):
        """Send a API PATCH to update Alert.dismissed to True"""

        alert = self.make_alertstate(HostOfflineAlert, dismissed=False, severity=WARNING, created_at=timezone.now())
        self.assertEqual(alert.dismissed, False)

        path = "/api/alert/%s/" % alert.pk
        # reject if severity isn't descriptive string as per the api
        response = self.api_client.patch(path, data={"dismissed": True, "severity": 10})
        self.assertHttpBadRequest(response)
        response = self.api_client.patch(path, data={"dismissed": True})
        self.assertHttpAccepted(response)

        alert = freshen(alert)
        self.assertEqual(alert.dismissed, True)


class TestPatchDismissablesWithDeletedRelatedObject(NotificationTestCase):
    """After the first load the UI can request updates based on date

    Sending all fields as strings to simulate what I think the FE does
    """

    def test_dismissing_alert(self):
        """Send a API PATCH to update Alert.dismissed to True with del obj

        HostOfflineAlert.alert_item is a GenericForeignKey.  This will test that
        item being set, but deleted
        """

        alert = self.make_alertstate(HostOfflineAlert, dismissed=False, severity=WARNING, created_at=timezone.now())
        self.assertEqual(alert.dismissed, False)

        self.assertEqual(type(alert.alert_item), ManagedHost)
        alert.alert_item.mark_deleted()

        #  Make sure it is deleted.
        self.assertRaises(ManagedHost.DoesNotExist, ManagedHost.objects.get, pk=alert.alert_item.pk)

        #  Should not be able to PATCH this to dismissed without a failure
        data = {"dismissed": True}
        response = self.api_client.patch("/api/alert/%s/" % alert.pk, data=data)
        self.assertHttpAccepted(response)

        alert = freshen(alert)
        self.assertEqual(alert.dismissed, True)


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

        alert = self.make_alertstate(HostOfflineAlert, dismissed=False, severity=WARNING, created_at=timezone.now())
        self.assertEqual(alert.dismissed, False)

        self.api_client.client.logout()

        data = {"dismissed": True}
        response = self.api_client.patch("/api/alert/%s/" % alert.pk, data=data)
        self.assertHttpUnauthorized(response)

        alert = freshen(alert)
        self.assertEqual(alert.dismissed, False)


class TestFSAdminsCanDismiss(NotificationTestCase):
    """Make sure filesystem_administrators can Dismiss or Dismiss all alerts

    Bug HYD-2619
    """

    def __init__(self, methodName=None):
        super(TestFSAdminsCanDismiss, self).__init__(methodName, username="debug", password="lustre")

    def test_dismissing_alert(self):
        """Test dismissing alert by fs admins is allowed"""

        alert = self.make_alertstate(HostOfflineAlert, dismissed=False, severity=WARNING, created_at=timezone.now())
        self.assertEqual(alert.dismissed, False)

        data = {"dismissed": True}
        response = self.api_client.patch("/api/alert/%s/" % alert.pk, data=data)

        self.assertHttpAccepted(response)

        alert = freshen(alert)
        self.assertEqual(alert.dismissed, True)


class TestFSUsersCannotDismiss(NotificationTestCase):
    """Make sure filesystem_users cannot Dismiss or Dismiss all alerts"""

    def __init__(self, methodName=None):
        super(TestFSUsersCannotDismiss, self).__init__(methodName, username="user", password="lustre")

    def test_dismissing_alert(self):
        """Test dismissing alert by fs users is prevented"""

        alert = self.make_alertstate(HostOfflineAlert, dismissed=False, severity=WARNING, created_at=timezone.now())
        self.assertEqual(alert.dismissed, False)

        data = {"dismissed": True}
        response = self.api_client.patch("/api/alert/%s/" % alert.pk, data=data)
        self.assertHttpUnauthorized(response)

        alert = freshen(alert)
        self.assertEqual(alert.dismissed, False)
