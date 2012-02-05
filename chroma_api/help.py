#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from hydraapi.requesthandler import AnonymousRESTRequestHandler, APIResponse

import configure.lib.conf_param
from configure.models import ManagedOst, ManagedMdt, ManagedFilesystem


class ConfParamHandler(AnonymousRESTRequestHandler):
    def get(self, request, kind = None, keys = None):
        """
         One of 'kind' or 'keys' must be set

         :param keys: comma separated list of strings
         :param kind: one of 'OST', 'MDT' or 'FS'"""
        if kind:
            klass = {
                    "OST": ManagedOst,
                    "MDT": ManagedMdt,
                    "FS": ManagedFilesystem
                    }[kind]

            return configure.lib.conf_param.get_possible_conf_params(klass)
        elif keys:
            keys = keys.split(",")
            return dict([(key, configure.lib.conf_param.get_conf_param_help(key)) for key in keys])
        else:
            return APIResponse(None, 400)
