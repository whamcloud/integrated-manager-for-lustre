#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from configure.models import Command
from hydraapi.requesthandler import RequestHandler
from django.shortcuts import get_object_or_404


class Handler(RequestHandler):
    def get(self, request, id = None):
        if id:
            command = get_object_or_404(Command, id = id)
            return command.to_dict()
        else:
            return [c.to_dict() for c in Command.objects.all()]
