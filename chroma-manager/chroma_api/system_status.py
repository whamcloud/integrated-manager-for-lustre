#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import traceback

from tastypie.resources import  Resource
from tastypie.authorization import  Authorization
from tastypie import fields

from chroma_core.lib.service_config import SupervisorStatus
from chroma_core.services import log_register
from chroma_api.authentication import AnonymousAuthentication


log = log_register(__name__)


class StatusAuthorization(Authorization):
    """
    Limit access to superusers
    """
    def is_authorized(self, request, object=None):
        return request.user.groups.filter(name = 'superusers').exists()


class SystemStatus(object):
    def __init__(self):
        self.supervisor_status = SupervisorStatus()


class SystemStatusResource(Resource):
    """
    The internal status of this server.
    """

    supervisor = fields.DictField(help_text = "Status of the supervisor daemon")

    class Meta:
        object_class = SystemStatus
        resource_name = 'system_status'
        authorization = StatusAuthorization()
        authentication = AnonymousAuthentication()

        fields = ['supervisor']

        list_allowed_methods = ['get']
        detail_allowed_methods = []

    def get_resource_uri(self, bundle):
        return self.get_resource_list_uri()

    def dehydrate_supervisor(self, bundle):
        try:
            return bundle.obj.supervisor_status.get_all_process_info()
        except Exception:
            # Broad exception handler because we never want to 500 requests for
            # system status during debugging
            log.error("Exception getting supervisor state: %s" % (traceback.format_exc()))
            return None

    def get_list(self, request = None, **kwargs):
        bundle = self.build_bundle(obj = SystemStatus(), request = request)
        bundle = self.full_dehydrate(bundle)
        return self.create_response(request, bundle)
