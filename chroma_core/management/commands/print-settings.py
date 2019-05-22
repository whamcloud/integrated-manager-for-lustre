# Copyright (c) 2018 DDN. All rights reserved.
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

        source_map_paths = glob.glob("/usr/share/iml-manager/iml-gui/main*.map")
        SOURCE_MAP_PATH = next(iter(source_map_paths), None)

        DB = settings.DATABASES.get("default")
        xs = map(
            lambda x: "{0}={1}".format(x[0], x[1]),
            [
                ("REALTIME_PORT", settings.REALTIME_PORT),
                ("VIEW_SERVER_PORT", settings.VIEW_SERVER_PORT),
                ("WARP_DRIVE_PORT", settings.WARP_DRIVE_PORT),
                ("MAILBOX_PORT", settings.MAILBOX_PORT),
                ("HTTP_AGENT2_PORT", settings.HTTP_AGENT2_PORT),
                ("HTTP_AGENT2_PROXY_PASS", settings.HTTP_AGENT2_PROXY_PASS),
                ("ALLOW_ANONYMOUS_READ", json.dumps(settings.ALLOW_ANONYMOUS_READ)),
                ("BUILD", settings.BUILD),
                ("IS_RELEASE", json.dumps(settings.IS_RELEASE)),
                ("LOG_PATH", settings.LOG_PATH),
                ("SERVER_HTTP_URL", settings.SERVER_HTTP_URL),
                ("SITE_ROOT", settings.SITE_ROOT),
                ("VERSION", settings.VERSION),
                ("API_USER", API_USER),
                ("API_KEY", API_KEY),
                ("SOURCE_MAP_PATH", SOURCE_MAP_PATH),
                ("PROXY_HOST", settings.PROXY_HOST),
                ("DB_HOST", DB.get("HOST")),
                ("DB_NAME", DB.get("NAME")),
                ("DB_USER", DB.get("USER")),
                ("DB_PASSWORD", DB.get("PASSWORD")),
                ("AMQP_BROKER_USER", settings.AMQP_BROKER_USER),
                ("AMQP_BROKER_PASSWORD", settings.AMQP_BROKER_PASSWORD),
                ("AMQP_BROKER_VHOST", settings.AMQP_BROKER_VHOST),
                ("AMQP_BROKER_HOST", settings.AMQP_BROKER_HOST),
                ("AMQP_BROKER_PORT", settings.AMQP_BROKER_PORT),
            ],
        )

        print("\n".join(xs))
