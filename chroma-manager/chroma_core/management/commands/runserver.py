#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from django.core.management.commands.runserver import Command as BaseCommand
from chroma_core.services.log import log_set_filename


class Command(BaseCommand):
    """
    Add logging setup to the normal runserver command
    """
    def handle(self, *args, **kwargs):
        log_set_filename('runserver.log')
        super(Command, self).handle(*args, **kwargs)
