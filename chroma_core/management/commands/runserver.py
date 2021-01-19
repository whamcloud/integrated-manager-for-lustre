# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from django.core.management.commands.runserver import Command as BaseCommand
from chroma_core.services.log import log_set_filename


class Command(BaseCommand):
    """
    Add logging setup to the normal runserver command
    """

    def handle(self, *args, **kwargs):
        log_set_filename("runserver.log")
        super(Command, self).handle(*args, **kwargs)
