
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

# Create your views here.
from django.core.management import setup_environ
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponse
from django.utils.cache import add_never_cache_headers

import settings
setup_environ(settings)

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

def get_db_logs(request):
    from hydraapi.monitorapi import get_logs
    log_result = get_logs(request.GET.get('host_id',None),
                          request.GET.get('start_time',None),
                          request.GET.get('end_time',None),
                          request.GET.get('lustre'),
                          int(request.GET.get('iDisplayStart',0)),
                          min(int(request.GET.get('iDisplayLength',10)),100),
                          request.GET.get('sSearch', '').encode('utf-8'),
                          int(request.GET.get('iSortingCols',0)))
    return send_datatable_response(log_result,int(request.GET.get('sEcho',0)))

def get_db_events(request):
    from hydraapi.monitorapi import geteventsbyfilter
    event_result = geteventsbyfilter(request.GET.get('host_id',None),
                                     request.GET.get('severity',None),
                                     request.GET.get('event_type'),
                                     int(request.GET.get('iDisplayStart',0)),
                                     min(int(request.GET.get('iDisplayLength',10)),100),
                                     int(request.GET.get('iSortingCols',0)))  
    return send_datatable_response(event_result,int(request.GET.get('sEcho',0)))
    
def send_datatable_response(result,sEcho):
    import json 

    response_dict = {}
    response_dict.update({'aaData':result['aaData']})
    response_dict.update({'sEcho': sEcho, 'iTotalRecords': result['iTotalRecords'], 'iTotalDisplayRecords':result['iTotalDisplayRecords']})
    response =  HttpResponse(json.dumps(response_dict), mimetype='application/javascript')
    #prevent from caching datatables result
    add_never_cache_headers(response)
    return response
