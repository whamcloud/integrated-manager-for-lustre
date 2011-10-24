#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

# REST API Conrtoller for Hydra server Audit resource.
# 
from django.core.management import setup_environ

# Hydra Server Imports
import settings
setup_environ(settings)

from requesthandler import (AnonymousRequestHandler)
from configure.models import Monitor

#REST API Controler for Hydra audit related operations/actions
class HydraAudit(AnonymousRequestHandler):
    def run(self,request):
        audit_list = []
        for m in Monitor.objects.all():
            from celery.result import AsyncResult
            if m.task_id:
                task_state = AsyncResult(m.task_id).state
            else:
                task_state = ""
            audit_list.append(
                              {
                               'host' : m.host,
                               'state': m.state,
                               'task_id' : m.task_id,
                               'task_state' : task_state
                              }    
            )
            return audit_list

class ClearAudit(AnonymousRequestHandler):     
    def run(self,request):
        audit_list = []
        for m in Monitor.objects.all():
            m.update(state = 'idle',task_id = None)
            audit_list.append(
                              {
                               'host' : m.host,
                               'state': m.state,
                               'task_id' : m.task_id,
                               'audit_cleared' : 'True' 
                              }
            )  
        return audit_list
