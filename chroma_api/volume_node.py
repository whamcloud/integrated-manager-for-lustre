#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from chroma_core.models import LunNode
from chroma_api.requesthandler import RequestHandler
from django.shortcuts import get_object_or_404


class Handler(RequestHandler):
    def get(cls, request, id = None):
        if id:
            return get_object_or_404(LunNode, id = id).to_dict()
        else:
            return [l.to_dict() for l in LunNode.objects.all()]
