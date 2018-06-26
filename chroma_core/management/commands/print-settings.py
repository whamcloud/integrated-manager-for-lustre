# Copyright (c) 2018 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import settings
import glob
import json
from django.db import connection
from django.core.management.commands.runserver import Command as BaseCommand


class Command(BaseCommand):
    """
    Prints out selected settings in env variable format
    """
    help = """Prints out selected settings in env variable format"""

    def handle(self, *args, **kwargs):
        cursor = connection.cursor()
        cursor.execute("SELECT * from api_key()")
        (API_USER, API_KEY) = cursor.fetchone()
        cursor.close()

        source_map_paths = glob.glob(
            '/usr/share/iml-manager/iml-gui/main*.map')
        SOURCE_MAP_PATH = next(iter(source_map_paths), None)

        xs = map(lambda (x, y): "{0}={1}".format(x, y), [
            ("LOG_PATH", settings.LOG_PATH),
            ("REALTIME_PORT", settings.REALTIME_PORT),
            ("SERVER_HTTP_URL", settings.SERVER_HTTP_URL),
            ("ALLOW_ANONYMOUS_READ", json.dumps(
                settings.ALLOW_ANONYMOUS_READ)),
            ("BUILD", settings.BUILD),
            ("IS_RELEASE", json.dumps(settings.IS_RELEASE)),
            ("LOG_PATH", settings.LOG_PATH),
            ("SERVER_HTTP_URL", settings.SERVER_HTTP_URL),
            ("SITE_ROOT", settings.SITE_ROOT),
            ("VIEW_SERVER_PORT", settings.VIEW_SERVER_PORT),
            ("VERSION", settings.VERSION),
            ("API_USER", API_USER),
            ("API_KEY", API_KEY),
            ("SOURCE_MAP_PATH", SOURCE_MAP_PATH),
        ])

        print '\n'.join(xs)
