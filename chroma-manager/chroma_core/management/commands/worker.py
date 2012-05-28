#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from django.core.management.base import CommandError
from djcelery.management.commands.celeryd import Command as DjangoCeleryCommand
from chroma_core.lib.service_config import ServiceConfig


class Command(DjangoCeleryCommand):
    def handle(self, *args, **options):
        if not ServiceConfig().configured():
            raise CommandError("Chroma is not configured, please run chroma-config setup")

        super(Command, self).handle(*args, **options)
