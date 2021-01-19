# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import logging

from chroma_core.lib.storage_plugin.base_alert_condition import AlertCondition


class BoundCondition(AlertCondition):
    upper = None

    def __init__(self, attribute, error_bound=None, warn_bound=None, info_bound=None, message=None, *args, **kwargs):
        self.error_bound = error_bound
        self.warn_bound = warn_bound
        self.info_bound = info_bound
        self.attribute = attribute
        self.message = message
        super(BoundCondition, self).__init__(*args, **kwargs)

    def alert_classes(self):
        result = []
        bound_sev = [
            (self.error_bound, logging.ERROR),
            (self.warn_bound, logging.WARNING),
            (self.info_bound, logging.INFO),
        ]
        for bound, sev in bound_sev:
            if bound == None:
                continue
            else:
                alert_name = "_%s_%s_%s" % (self._id, self.attribute, sev)
                result.append(alert_name)

        return result

    def test(self, resource):
        result = []
        bound_sev = [
            (self.error_bound, logging.ERROR),
            (self.warn_bound, logging.WARNING),
            (self.info_bound, logging.INFO),
        ]
        for bound, sev in bound_sev:
            if bound == None:
                continue
            alert_name = "_%s_%s_%s" % (self._id, self.attribute, sev)
            if self.upper:
                active = getattr(resource, self.attribute) > bound
            else:
                active = getattr(resource, self.attribute) < bound

            result.append([alert_name, self.attribute, active, sev])

        return result


class UpperBoundCondition(BoundCondition):
    """A condition that checks a numeric attribute against an upper bound, and
    raises the alert if it exceeds that bound
    ::

     UpperBoundCondition('temperature', error_bound = 85, message = "Maximum operating temperature exceeded")
    """

    upper = True


class LowerBoundCondition(BoundCondition):
    """A condition that checks a numeric attribute against a lower bound, and
    raises the alert if it falls below that bound
    ::

     LowerBoundCondition('rate', error_bound = 10, message = "Rate too low")
    """

    upper = False


class ValueCondition(AlertCondition):
    """A condition that checks an attribute against certain values indicating varying
    severities of alert.  For example, if you had a 'status' attribute on your
    'widget' resource class which could be 'OK' or 'FAILED' then you might
    create an AttrValAlertCondition like this:
    ::

        AttrValAlertCondition('status', error_states = ['FAILED'], message = "Widget failed")"""

    def __init__(
        self,
        attribute,
        error_states=list([]),
        warn_states=list([]),
        info_states=list([]),
        message=None,
        *args,
        **kwargs
    ):
        self.error_states = error_states
        self.warn_states = warn_states
        self.info_states = info_states
        self.attribute = attribute
        self.message = message
        super(ValueCondition, self).__init__(*args, **kwargs)

    def alert_classes(self):
        result = []
        states_sev = [
            (self.error_states, logging.ERROR),
            (self.warn_states, logging.WARNING),
            (self.info_states, logging.INFO),
        ]
        for states, sev in states_sev:
            if len(states) == 0:
                continue
            else:
                alert_name = "_%s_%s_%s" % (self._id, self.attribute, sev)
                result.append(alert_name)

        return result

    def test(self, resource):
        result = []
        states_sev = [
            (self.error_states, logging.ERROR),
            (self.warn_states, logging.WARNING),
            (self.info_states, logging.INFO),
        ]
        for states, sev in states_sev:
            if len(states) == 0:
                continue
            alert_name = "_%s_%s_%s" % (self._id, self.attribute, sev)
            active = getattr(resource, self.attribute) in states
            result.append([alert_name, self.attribute, active, sev])

        return result
