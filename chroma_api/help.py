#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from hydraapi.requesthandler import RequestHandler, APIResponse

import chroma_core.lib.conf_param
from chroma_core.models import ManagedOst, ManagedMdt, ManagedFilesystem


class ConfParamHandler(RequestHandler):
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

            return chroma_core.lib.conf_param.get_possible_conf_params(klass)
        elif keys:
            keys = keys.split(",")
            return dict([(key, chroma_core.lib.conf_param.get_conf_param_help(key)) for key in keys])
        else:
            return APIResponse(None, 400)
