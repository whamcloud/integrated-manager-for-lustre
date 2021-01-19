# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import threading

from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db.models import Count

from chroma_core.services import log_register
from chroma_core.models.alert import AlertState, AlertEmail


logging = log_register("email_alerts")


class MailAlerts(threading.Thread):
    def __init__(self, sender, subject_prefix, host):
        super(MailAlerts, self).__init__()

        self.sender = sender
        self.subject_prefix = subject_prefix
        self.host = host
        self.change_event = threading.Event()
        self.exit = False

        post_save.connect(self._table_changed)

    def run(self):
        while self.exit is False:
            try:
                self.change_event.wait()
                self.change_event.clear()

                if self.exit:
                    break

                alerts = AlertState.objects.filter(alertemail=None, dismissed=False)

                # Now filter the types that send mail alerts.
                alerts = [alert for alert in alerts if alert.require_mail_alert]

                if alerts:
                    alert_email = AlertEmail()
                    alert_email.save()
                    alert_email.alerts.add(*alerts)
                    alert_email.save()

                    self._send_alerts_email(alert_email)
            except Exception as exception:
                logging.warning(str(exception))

    def stop(self):
        post_save.disconnect(self._table_changed)

        self.exit = True
        self.change_event.set()

    def _table_changed(self, sender, **kwargs):
        if sender._meta.db_table == AlertState._meta.db_table:
            self.change_event.set()

    def _send_alerts_email(self, alert_email):
        for user in User.objects.annotate(num_subscriptions=Count("alert_subscriptions")).filter(
            num_subscriptions__gt=0
        ):
            alert_messages = []
            subscriptions = [subscription.alert_type_name for subscription in user.alert_subscriptions.all()]
            for alert in AlertState.objects.filter(id__in=alert_email.alerts.all(), record_type__in=subscriptions):
                alert_message = "%s %s" % (alert.begin, alert.message())
                if alert.active:
                    alert_message += "  Alert state is currently active"
                alert_messages.append(alert_message)

            if self.host and len(alert_messages) > 0:
                message = "New Chroma Alerts:\n" + "\n".join(alert_messages)
                send_mail(self.subject_prefix, message, self.sender, [user.email])
