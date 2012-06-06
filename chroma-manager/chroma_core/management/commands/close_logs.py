#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Invoke the close_logs celery remote control operation"""
    def handle(self, *args, **kwargs):
        from celery.task.control import broadcast
        print broadcast('close_logs', reply = True)
