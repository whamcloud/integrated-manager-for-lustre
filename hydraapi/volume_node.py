#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from configure.models import LunNode
from hydraapi.requesthandler import RequestHandler
from django.shortcuts import get_object_or_404


class Handler(RequestHandler):
    def get(cls, request, id = None):
        if id:
            return get_object_or_404(LunNode, id = id).to_dict()
        else:
            return [l.to_dict() for l in LunNode.objects.all()]
