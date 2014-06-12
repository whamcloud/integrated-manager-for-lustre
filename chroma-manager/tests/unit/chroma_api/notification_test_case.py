import logging

from chroma_core.models import (Command, HostOfflineAlert, ManagedHost, Event, AlertState, SyslogEvent)

from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase
from tests.unit.chroma_core.helper import freshen, synthetic_host, random_str

INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR


class NotificationTestCase(ChromaApiTestCase):
    """TestCase to create Alerts, Events and Commands for testing"""

    def make_host_notification(self,
                               notification_obj_type,
                               host = None,
                               dismissed=False,
                               severity=INFO,
                               date=None,
                               failed=None,
                               complete=False,
                               message='test'):
        """Create one of 3 types of objects that can be dismissed by a user"""

        if issubclass(notification_obj_type, AlertState):
            return self.make_alertstate(notification_obj_type,
                                        dismissed=dismissed,
                                        severity=severity,
                                        created_at=date,
                                        alert_item=host)
        elif notification_obj_type == Event:
            return self.make_event(dismissed=dismissed,
                                   severity=severity,
                                   created_at=date,
                                   host=host)
        elif notification_obj_type == Command:
            return self.make_command(dismissed=dismissed,
                                     created_at=date,
                                     failed=failed,
                                     complete=complete,
                                     message=message)

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

    def make_command(self, dismissed=False, complete=False, created_at=None, failed=True, message='test'):

        command = Command.objects.create(dismissed=dismissed,
            message=message,
            complete=complete,
            errored=failed)

        #  Command.created_at is auto_add_now - so have to update it
        if created_at is not None:
            command.created_at = created_at
            command.save()
            command = freshen(command)

        return command

    def make_alertstate(self, alert_obj=HostOfflineAlert, alert_item=None, dismissed=False, severity=INFO,
                        created_at=None, active=False):

        if alert_item is None:
            alert_item = synthetic_host()

        alert_type = alert_item.__class__.__name__

        # The following fields must be unique together for each AlertState
        # alert_item_type, alert_item_id, alert_type, active
        # item_type and item_id are the content_type and pk of alert_item
        return alert_obj.objects.create(severity=severity,
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

        address = random_str(postfix=".tld")
        nodename = 'node-name'
        self.host = ManagedHost.objects.create(
            address=address,
            fqdn="%s.%s" % (nodename, address),
            nodename=nodename)

        return self.host

    def dump_objects(self, objects):
        return "\n" + "\n\n".join([repr(o) for o in objects])
