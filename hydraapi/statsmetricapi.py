#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================
# REST API Conrtoller for Lustre File systems resource monitor name space
from django.core.management import setup_environ

# Hydra server imports
import settings
setup_environ(settings)

from requesthandler import (AnonymousRequestHandler,
                            extract_request_args,
                            extract_exception)
from monitor.models import (Filesystem,
                            MetadataTarget,
                            ManagementTarget,
                            ObjectStoreTarget,
                            Host)

# Logger Settings
import logging
hydraapi_log = logging.getLogger('hydraapi')
hydraapi_log.setLevel(logging.DEBUG)
handler = logging.FileHandler(settings.API_LOG_PATH)
handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', '%d/%b/%Y:%H:%M:%S'))
hydraapi_log.addHandler(handler)
if settings.DEBUG:
    hydraapi_log.setLevel(logging.DEBUG)
    hydraapi_log.addHandler(logging.StreamHandler())
else:
    hydraapi_log.setLevel(logging.INFO)

class GetFSTargetStats(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_stats_for_fs_targets)

    @classmethod
    @extract_request_args(filesystem_name='filesystem',start_time='starttime',end_time='endtime',data_function='datafunction',fetch_metrics='fetchmetrics')
    @extract_exception
    def get_stats_for_fs_targets(self,request,filesystem_name,start_time,end_time ,data_function,fetch_metrics):
        #try:
            if filesystem_name :
                fs = Filesystem.objects.get(name=filesystem_name)
                fs_ost_stats = fs.metrics.fetch_last(ObjectStoreTarget,fetch_metrics=fetch_metrics.split())    
                fs_mdt_stats = fs.metrics.fetch_last(MetadataTarget,fetch_metrics=fetch_metrics.split())
                fs_ost_stats.extend(fs_mdt_stats)
                return fs_ost_stats   
            else :
                all_stats = []
                for filesystem in Filesystem.objects.all():
                    fs = Filesystem.objects.get(name=filesystem_name)
                    fs_ost_stats = fs.metrics.fetch_last(ObjectStoreTarget,fetch_metrics=fetch_metrics.split())
                    fs_mdt_stats = fs.metrics.fetch_last(MetadataTarget,fetch_metrics=fetch_metrics.split())
                    fs_ost_stats.extend(fs_mdt_stats)
                    all_stats.extend(fs_ost_stats)  
                return fs_ost_stats 
        #except:
        #    raise  Exception('POST call API_Exception:get_stats_for_fs_targets(filesystem_name,start_time,end_time ,data_function) => Failed to get data for inputs filesystem=%s|starttime=%s|endtime%s |datafunction=%s' %filesystem_name %start_time %end_time %data_function)

class GetTargetStats(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_fs_indoesusage)

    @classmethod
    @extract_request_args(target_name='filesystem',start_time='starttime',end_time='endtime' ,data_function='datafunction',fetch_metrics='fetchmetrics')
    @extract_exception
    def get_stats_for_target(self,request,filesystem_name,start_time,end_time ,data_function,fetch_metrics):
            return ''

class GetServerStats(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_stats_for_server)

    @classmethod
    @extract_request_args(host_name='hostname',start_time='starttime',end_time='endtime' ,data_function='datafunction',fetch_metrics='fetchmetrics')
    @extract_exception
    def get_stats_for_server(self,request,host_name,start_time,end_time ,data_function,fetch_metrics):
            return ''

class GetMDTStats(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_stats_for_mdt)

    @classmethod
    @extract_request_args(mdt_name='mdtname',start_time='starttime',end_time='endtime' ,data_function='datafunction',fetch_metrics='fetchmetrics')
    @extract_exception
    def get_stats_for_mdt(self,request,mdt_name,start_time,end_time ,data_function,fetch_metrics):
            return ''

class GetMDSStats(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_stats_for_mds)

    @classmethod
    @extract_request_args(mds_name='mdsname',start_time='starttime',end_time='endtime' ,data_function='datafunction',fetch_metrics='fetchmetrics')
    @extract_exception
    def get_stats_for_mds(self,request,mds_name,start_time,end_time ,data_function,fetch_metrics):
            return ''

