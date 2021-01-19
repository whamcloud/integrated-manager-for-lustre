# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import socket

import traceback
import requests
from django.db import connection
from requests.auth import HTTPBasicAuth
import settings

from tastypie.resources import Resource
from tastypie.authorization import Authorization
from tastypie import fields

from chroma_core.services import log_register
from chroma_api.authentication import AnonymousAuthentication


log = log_register(__name__)


class StatusAuthorization(Authorization):
    """
    Limit access to superusers
    """

    def is_authorized(self, request, object=None):
        return request.user.groups.filter(name="superusers").exists()


def _get_table(table, silence_columns=[]):
    "Returns all rows from a cursor as a dict"

    cursor = connection.cursor()
    cursor.execute("SELECT * FROM %s;" % table)
    desc = cursor.description

    select_columns = []
    columns = [col[0] for col in desc]
    for i, col_name in enumerate(columns):
        if col_name not in silence_columns:
            select_columns.append(i)

    return {
        "columns": [columns[i] for i in select_columns],
        "rows": [[row[i] for i in select_columns] for row in cursor.fetchall()],
    }


class SystemStatus(object):
    def get_postgres_stats(self):
        result = {
            "pg_stat_activity": _get_table(
                "pg_stat_activity",
                silence_columns=["xact_start", "query_start", "backend_start", "client_port", "client_addr", "datid"],
            ),
            "table_stats": {},
        }
        for table in ["pg_stat_user_tables", "pg_statio_user_tables"]:
            result["table_stats"][table] = _get_table(table, silence_columns=["relid", "schemaname"])

        return result

    def get_rabbitmq(self):
        url = "http://{}:{}@{}:15672/api/queues/{}/".format(
            settings.AMQP_BROKER_USER,
            settings.AMQP_BROKER_PASSWORD,
            settings.AMQP_BROKER_HOST,
            settings.AMQP_BROKER_VHOST,
        )

        try:
            response = requests.get(
                url,
                auth=HTTPBasicAuth(settings.AMQP_BROKER_USER, settings.AMQP_BROKER_PASSWORD),
                proxies={"http": None},
            )
        except (socket.error, requests.exceptions.ConnectionError) as e:
            log.error("Error %s connecting to %s" % (e, url))
            return None
        else:
            if not response.ok:
                log.error("Error getting rabbitmq info: %s %s\n%s" % (response.status_code, url, response.content))
                return None

        queues = response.json()

        for queue in queues:
            for event in ["publish", "ack"]:
                if "message_stats" in queue and "%s_details" % event in queue["message_stats"]:
                    queue["message_stats_%s_details_rate" % event] = queue["message_stats"]["%s_details" % event][
                        "rate"
                    ]
                else:
                    queue["message_stats_%s_details_rate" % event] = 0

        return {"queues": queues}


class SystemStatusResource(Resource):
    """
    The internal status of this server.
    """

    postgres = fields.DictField(help_text="PostgreSQL statistics")
    rabbitmq = fields.DictField(help_text="RabbitMQ statistics")

    class Meta:
        object_class = SystemStatus
        resource_name = "system_status"
        authorization = StatusAuthorization()
        authentication = AnonymousAuthentication()

        list_allowed_methods = ["get"]
        detail_allowed_methods = []

    def get_resource_uri(self, bundle=None, url_name=None):
        return Resource.get_resource_uri(self)

    def dehydrate_rabbitmq(self, bundle):
        return bundle.obj.get_rabbitmq()

    def dehydrate_postgres(self, bundle):
        return bundle.obj.get_postgres_stats()

    def get_list(self, request=None, **kwargs):
        bundle = self.build_bundle(obj=SystemStatus(), request=request)
        bundle = self.full_dehydrate(bundle)
        return self.create_response(request, bundle)
