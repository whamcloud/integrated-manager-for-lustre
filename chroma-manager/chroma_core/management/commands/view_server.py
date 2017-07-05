# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import os
import settings
import json

from django.core.management.commands.runserver import Command as BaseCommand


class Command(BaseCommand):
    """
    Setup view-server
    """
    help = """Generates a conf.json file and starts the view-server."""

    def handle(self, *args, **kwargs):
        """
        Generate config a file for the view-server, and send the view-server command to stdout.

        The reason for sending the command to stdout instead of just running
        it is so that supervisord can directly manage the resulting
        process (otherwise we would have to handle passing signals through).
        """
        from chroma_core.lib.util import site_dir

        SITE_ROOT = site_dir()
        VIEW_SERVER_DIR = os.path.join(SITE_ROOT, 'ui-modules', 'node_modules', '@iml', 'view-server', 'dist')
        CONF = os.path.join(VIEW_SERVER_DIR, "conf.json")

        conf = {
            "ALLOW_ANONYMOUS_READ": settings.ALLOW_ANONYMOUS_READ,
            "BUILD": settings.BUILD,
            "IS_RELEASE": settings.IS_RELEASE,
            "LOG_PATH": settings.LOG_PATH,
            "SERVER_HTTP_URL": settings.SERVER_HTTP_URL,
            "SITE_ROOT": settings.SITE_ROOT,
            "VIEW_SERVER_PORT": settings.VIEW_SERVER_PORT,
            "VERSION": settings.VERSION
        }

        json.dump(conf, open(CONF, 'w'), indent=2)

        cmdline = ["node", VIEW_SERVER_DIR + '/bundle.js']
        print " ".join(cmdline)
