# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


"""
The service `job_scheduler` handles both RPCs (JobSchedulerRpc) and a queue (NotificationQueue).
The RPCs are used for explicit requests to modify the system or run a particular task, while the queue
is used for updates received from agent reports.  Access to both of these, along with some additional
non-remote functionality is wrapped in JobSchedulerClient.

"""
import datetime

from django.contrib.contenttypes.models import ContentType
from django.db.models import DateTimeField

from chroma_core.services import log_register
from chroma_core.services.queue import ServiceQueue
from disabled_connection import DisabledConnection


log = log_register(__name__)


class NotificationQueue(ServiceQueue):
    name = "job_scheduler_notifications"


def notify(instance, time, update_attrs, from_states=[]):
    """Having detected that the state of an object in the database does not
    match information from real life (i.e. chroma-agent), call this to
    request an update to the object.

    :param instance: An instance of a StatefulObject
    :param time: A UTC datetime.datetime object
    :param update_attrs: Dict of attribute name to json-serializable value of the changed attributes
    :param from_states: (Optional) A list of states from which the instance may be
                        set to the new state.  This lets updates happen
                        safely without risking e.g. notifying an 'unconfigured'
                        LNet state to 'lnet_down'.  If this is ommitted, the notification
                        will be applied irrespective of the object's state.

    :return: None

    """

    if (not from_states) or instance.state in from_states:
        log.info("Enqueuing notify %s at %s:" % (instance, time))
        for attr, value in update_attrs.items():
            try:
                log.info("  .%s %s->%s" % (attr, getattr(instance, attr), value))
            except DisabledConnection.DisabledConnectionUsed:
                log.info("  .%s 'Unknown State'->%s" % (attr, value))

        # Encode datetimes
        encoded_attrs = {}
        for attr, value in update_attrs.items():
            try:
                field = next(f for f in instance._meta.fields if f.name == attr)
            except StopIteration:
                # e.g. _id names, they can't be datetimes so pass through
                encoded_attrs[attr] = value
            else:
                if isinstance(field, DateTimeField):
                    assert isinstance(value, datetime.datetime), "Attribute %s of %s must be datetime" % (
                        attr,
                        instance.__class__,
                    )
                    encoded_attrs[attr] = value.isoformat()
                else:
                    encoded_attrs[attr] = value

        time_serialized = time.isoformat()
        NotificationQueue().put(
            {
                "instance_natural_key": ContentType.objects.get_for_model(instance).natural_key(),
                "instance_id": instance.id,
                "time": time_serialized,
                "update_attrs": encoded_attrs,
                "from_states": from_states,
            }
        )
