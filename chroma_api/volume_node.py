#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from configure.models import LunNode
from requesthandler import AnonymousRESTRequestHandler
from django.shortcuts import get_object_or_404


class Handler(AnonymousRESTRequestHandler):
    def get(cls, request, id = None):
        if id:
            return get_object_or_404(LunNode, id = id).to_dict()
        else:
            return [l.to_dict() for l in LunNode.objects.all()]
