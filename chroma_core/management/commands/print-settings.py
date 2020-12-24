# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import settings
import glob
import json
import os
from django.db import connection
from django.core.management.commands.runserver import Command as BaseCommand


class Command(BaseCommand):
    """
    Prints out selected settings in env variable format
    """

    help = """Prints out selected settings in env variable format"""

    def handle(self, *args, **kwargs):
        cursor = connection.cursor()
        API_USER = "api"
        cursor.execute("SELECT * from api_key(%s)", [API_USER])
        API_KEY = cursor.fetchone()[0]
        cursor.close()

        cursor = connection.cursor()
        CLIENT_API_USER = "client_api"
        cursor.execute("SELECT * from api_key(%s)", [CLIENT_API_USER])
        CLIENT_API_KEY = cursor.fetchone()[0]
        cursor.close()

        DB = settings.DATABASES.get("default")

        config = {
            "WARP_DRIVE_PORT": settings.WARP_DRIVE_PORT,
            "MAILBOX_PORT": settings.MAILBOX_PORT,
            "REPORT_PORT": settings.REPORT_PORT,
            "DEVICE_AGGREGATOR_PORT": settings.DEVICE_AGGREGATOR_PORT,
            "HTTP_FRONTEND_PORT": settings.HTTP_FRONTEND_PORT,
            "HTTPS_FRONTEND_PORT": settings.HTTPS_FRONTEND_PORT,
            "HTTP_AGENT_PROXY_PASS": settings.HTTP_AGENT_PROXY_PASS,
            "HTTP_AGENT2_PORT": settings.HTTP_AGENT2_PORT,
            "HTTP_AGENT2_PROXY_PASS": settings.HTTP_AGENT2_PROXY_PASS,
            "HTTP_API_PROXY_PASS": settings.HTTP_API_PROXY_PASS,
            "IML_API_PORT": settings.IML_API_PORT,
            "IML_API_PROXY_PASS": settings.IML_API_PROXY_PASS,
            "WARP_DRIVE_PROXY_PASS": settings.WARP_DRIVE_PROXY_PASS,
            "MAILBOX_PROXY_PASS": settings.MAILBOX_PROXY_PASS,
            "REPORT_PROXY_PASS": settings.REPORT_PROXY_PASS,
            "SSL_PATH": settings.SSL_PATH,
            "DEVICE_AGGREGATOR_PROXY_PASS": settings.DEVICE_AGGREGATOR_PROXY_PASS,
            "UPDATE_HANDLER_PROXY_PASS": settings.UPDATE_HANDLER_PROXY_PASS,
            "GRAFANA_PORT": settings.GRAFANA_PORT,
            "GRAFANA_PROXY_PASS": settings.GRAFANA_PROXY_PASS,
            "INFLUXDB_SERVER_FQDN": settings.INFLUXDB_SERVER_FQDN,
            "INFLUXDB_PROXY_PASS": settings.INFLUXDB_PROXY_PASS,
            "TIMER_PORT": settings.TIMER_PORT,
            "TIMER_SERVER_FQDN": settings.TIMER_SERVER_FQDN,
            "TIMER_PROXY_PASS": settings.TIMER_PROXY_PASS,
            "ALLOW_ANONYMOUS_READ": json.dumps(settings.ALLOW_ANONYMOUS_READ),
            "BUILD": settings.BUILD,
            "IS_RELEASE": json.dumps(settings.IS_RELEASE),
            "LOG_PATH": settings.LOG_PATH,
            "SERVER_HTTP_URL": settings.SERVER_HTTP_URL,
            "SITE_ROOT": settings.SITE_ROOT,
            "VERSION": settings.VERSION,
            "API_USER": API_USER,
            "API_KEY": API_KEY,
            "CLIENT_API_USER": CLIENT_API_USER,
            "CLIENT_API_KEY": CLIENT_API_KEY,
            "REPORT_PATH": settings.REPORT_PATH,
            "PROXY_HOST": settings.PROXY_HOST,
            "INFLUXDB_IML_DB": settings.INFLUXDB_IML_DB,
            "INFLUXDB_STRATAGEM_SCAN_DB": settings.INFLUXDB_STRATAGEM_SCAN_DB,
            "INFLUXDB_IML_STATS_DB": settings.INFLUXDB_IML_STATS_DB,
            "INFLUXDB_IML_STATS_LONG_DURATION": settings.INFLUXDB_IML_STATS_LONG_DURATION,
            "INFLUXDB_PORT": settings.INFLUXDB_PORT,
            "DB_HOST": DB.get("HOST"),
            "DB_NAME": DB.get("NAME"),
            "DB_USER": DB.get("USER"),
            "DB_PASSWORD": DB.get("PASSWORD"),
            "REPO_PATH": settings.REPO_PATH,
            "AMQP_BROKER_USER": settings.AMQP_BROKER_USER,
            "AMQP_BROKER_PASSWORD": settings.AMQP_BROKER_PASSWORD,
            "AMQP_BROKER_VHOST": settings.AMQP_BROKER_VHOST,
            "AMQP_BROKER_HOST": settings.AMQP_BROKER_HOST,
            "AMQP_BROKER_PORT": settings.AMQP_BROKER_PORT,
            "AMQP_BROKER_URL": settings.BROKER_URL,
            "BRANDING": settings.BRANDING,
            "USE_STRATAGEM": settings.USE_STRATAGEM,
            "DBLOG_HW": settings.DBLOG_HW,
            "DBLOG_LW": settings.DBLOG_LW,
        }

        if settings.EXA_VERSION:
            config["EXA_VERSION"] = settings.EXA_VERSION

        xs = map(lambda x: "{0}={1}".format(x[0], x[1]), config.items())

        print("\n".join(xs))
