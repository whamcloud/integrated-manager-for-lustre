#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2014 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


from datetime import timedelta

from celery.beat import Scheduler
from celery.task import task, periodic_task

import settings


class EphemeralScheduler(Scheduler):
    """A scheduler which does not persist the schedule to disk because
      we only use high frequency things, so its no problem to just start
      from scratch when celerybeat restarts"""
    def setup_schedule(self):
        self.merge_inplace(self.app.conf.CELERYBEAT_SCHEDULE)
        self.install_default_entries(self.schedule)


@periodic_task(run_every=timedelta(seconds=settings.EMAIL_ALERTS_PERIOD))
def mail_alerts():
    from chroma_core.models.alert import AlertState, AlertEmail

    alerts = AlertState.objects.filter(alertemail = None, dismissed = False)
    if not alerts:
        # no un-e-mailed alerts yet so just bail
        return

    alert_email = AlertEmail()
    alert_email.save()
    alert_email.alerts.add(*alerts)
    alert_email.save()

    send_alerts_email.delay(id = alert_email.id)


@task()
def send_alerts_email(id):
    from chroma_core.models.alert import AlertState, AlertEmail
    from django.contrib.auth.models import User
    from django.core.mail import send_mail
    from django.db.models import Count

    alert_email = AlertEmail.objects.get(pk = id)

    for user in User.objects.annotate(num_subscriptions = Count('alert_subscriptions')).filter(num_subscriptions__gt = 0):
        alert_messages = []
        subscriptions = [s.alert_type for s in user.alert_subscriptions.all()]
        for alert in AlertState.objects.filter(id__in = alert_email.alerts.all(), content_type__in = subscriptions):
            alert_message = "%s %s" % (alert.begin, alert.message())
            if alert.active:
                alert_message += "  Alert state is currently active"
            alert_messages.append(alert_message)

        if settings.EMAIL_HOST and len(alert_messages) > 0:
            message = "New Chroma Alerts:\n" + "\n".join(alert_messages)
            send_mail('New Chroma Server alerts', message, settings.EMAIL_SENDER,
                      [user.email])
