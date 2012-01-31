
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

# Create your views here.
from django.shortcuts import render_to_response
from django.template import RequestContext


def dashboard(request):
    return render_to_response("index.html",
            RequestContext(request, {}))


def dbalerts(request):
    return render_to_response("db_alerts.html",
            RequestContext(request, {}))


def dbevents(request):
    return render_to_response("db_events.html",
            RequestContext(request, {}))


def dblogs(request):
    return render_to_response("db_logs.html",
            RequestContext(request, {}))
