import logging

from chroma_core.models import HostOfflineAlert

from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase
from tests.unit.chroma_core.helpers.synthentic_objects import synthetic_host

INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR


class NotificationTestCase(ChromaApiTestCase):
    """TestCase to create Alerts, Events and Commands for testing"""

    def make_alertstate(
        self, alert_obj=HostOfflineAlert, alert_item=None, dismissed=False, severity=INFO, created_at=None, active=False
    ):

        if alert_item is None:
            alert_item = synthetic_host()

        alert_type = alert_item.__class__.__name__

        # The following fields must be unique together for each AlertState
        # alert_item_type, alert_item_id, alert_type, active
        # item_type and item_id are the content_type and pk of alert_item
        return alert_obj.objects.create(
            severity=severity,
            active=active,
            alert_item=alert_item,
            begin=created_at,
            end=created_at,
            dismissed=dismissed,
            alert_type=alert_type,
        )

    def dump_objects(self, objects):
        return "\n" + "\n\n".join([repr(o) for o in objects])
