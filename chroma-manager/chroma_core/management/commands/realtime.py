# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import os
import settings
import json
import glob

from django.core.management.commands.runserver import Command as BaseCommand


class Command(BaseCommand):
    """
    Setup realtime module
    """
    help = """Generates a conf.json file and starts the realtime module."""

    def handle(self, *args, **kwargs):
        """
        Generate config files for the realtime module, and send the node realtime command to stdout.

        The reason for sending the command to stdout instead of just running
        it is so that supervisord can directly manage the resulting node
        process (otherwise we would have to handle passing signals through).
        """
        from chroma_core.lib.util import site_dir

        SITE_ROOT = site_dir()
        REALTIME_DIR = os.path.join(SITE_ROOT, 'ui-modules', 'node_modules', '@iml/realtime')
        CONF = os.path.join(REALTIME_DIR, "conf.json")

        conf = {
            "LOG_PATH": SITE_ROOT if not len(settings.LOG_PATH) else settings.LOG_PATH,
            "REALTIME_PORT": settings.REALTIME_PORT,
            "SERVER_HTTP_URL": settings.SERVER_HTTP_URL
        }

        source_map_glob = os.path.join(SITE_ROOT, "ui-modules", "node_modules", "@iml", "gui", "dist", "built*.map")
        source_map_paths = glob.glob(source_map_glob)

        if source_map_paths:
            conf["SOURCE_MAP_PATH"] = source_map_paths[0]

        json.dump(conf, open(CONF, 'w'), indent=2)

        cmdline = ["node", REALTIME_DIR + '/server.js']
        print " ".join(cmdline)
