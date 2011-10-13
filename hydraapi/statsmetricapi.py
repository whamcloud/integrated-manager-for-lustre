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
    @extract_request_args(filesystem_name='filesystem',start_time='starttime',end_time='endtime',data_function='datafunction',target_kind='targetkind',fetch_metrics='fetchmetrics')
    @extract_exception
    def get_stats_for_fs_targets(self,request,filesystem_name,start_time,end_time ,data_function,target_kind,fetch_metrics):
        interval=600
        if filesystem_name:
            fs = Filesystem.objects.get(name=filesystem_name)
            return self.metrics_fetch(fs,target_kind,fetch_metrics,start_time,end_time,interval)
        else:
            all_fs_stats = []
            for fs in Filesystem.objects.all():
                all_fs_stats.append(self.metrics_fetch(fs,target_kind,fetch_metrics,start_time,end_time,interval))

    @classmethod
    @extract_exception
    def metrics_fetch(self,fs,target_kind,fetch_metrics,start_time,end_time,interval):
        import time
        if target_kind == 'OST':
            if interval:
                if fetch_metrics:
                    fs_target_stats = fs.metrics.fetch('Average',ObjectStoreTarget,fetch_metrics=fetch_metrics.split(),start_time=int(time.time()-600))
                else:
                    fs_target_stats = fs.metrics.fetch('Average',ObjectStoreTarget,start_time=int(time.time()-600))
            elif start_time:
                if fetch_metrics:
                    fs_target_stats = fs.metrics.fetch('Average',ObjectStoreTarget,fetch_metrics=fetch_metrics.split(),start_time=int(time.time()-600))
                else:
                    fs_target_stats = fs.metrics.fetch('Average',ObjectStoreTarget,start_time=int(time.time()-600))
            else:
                if fetch_metrics:
                    fs_target_stats = fs.metrics.fetch_last(ObjectStoreTarget,fetch_metrics=fetch_metrics.split())
                else:
                    fs_target_stats = fs.metrics.fetch_last(ObjectStoreTarget)
        elif target_kind == 'MDT':
            if interval:
                if fetch_metrics:
                    fs_target_stats = fs.metrics.fetch('Average',MetadataTarget,fetch_metrics=fetch_metrics.split(),start_time=int(time.time()-600))
                else:
                    fs_target_stats = fs.metrics.fetch('Average',MetadataTarget,start_time=int(time.time()-600))
            elif start_time:
                if fetch_metrics:
                    fs_target_stats = fs.metrics.fetch('Average',MetadataTarget,fetch_metrics=fetch_metrics.split(),start_time=int(time.time()-600))
                else:
                    fs_target_stats = fs.metrics.fetch('Average',MetadataTarget,start_time=int(time.time()-600))
            else:
                if fetch_metrics:
                    fs_target_stats = fs.metrics.fetch_last(MetadataTarget,fetch_metrics=fetch_metrics.split())
                else:
                    fs_target_stats = fs.metrics.fetch_last(MetadataTarget)   
        else:
            if interval:
                if fetch_metrics:
                    fs_target_stats = fs.metrics.fetch('Average',fetch_metrics=fetch_metrics.split(),start_time=int(time.time()-600))
                else:
                    fs_target_stats = fs.metrics.fetch('Average',start_time=int(time.time()-600))
            elif start_time:
                if fetch_metrics:
                    fs_target_stats = fs.metrics.fetch('Average',fetch_metrics=fetch_metrics.split(),start_time=int(time.time()-600))
                else:
                    fs_target_stats = fs.metrics.fetch('Average',start_time=int(time.time()-600))
            else:
                if fetch_metrics:
                    fs_target_stats = fs.metrics.fetch_last(fetch_metrics=fetch_metrics.split())
                else:
                    fs_target_stats = fs.metrics.fetch_last()

        return fs_target_stats

class GetServerStats(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_stats_for_server)

    @classmethod
    @extract_request_args(host_name='hostname',start_time='starttime',end_time='endtime' ,data_function='datafunction',fetch_metrics='fetchmetrics')
    @extract_exception
    def get_stats_for_server(self,request,host_name,start_time,end_time ,data_function,fetch_metrics):
        if host_name:
            host = Host.objects.get(id=host_name)
            host_stats = host.metrics.fetch_last()
            return host_stats
        else:
            host_stats =[]
            for host in Host.objects.all():
                host_stat = host.metrics.fetch_last()
                host_stats.extend(host_stat)
            return host_stats


class GetMGSStats(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_stats_for_mds)

    @classmethod
    @extract_request_args(mgs_name='mgsname',start_time='starttime',end_time='endtime' ,data_function='datafunction',fetch_metrics='fetchmetrics')
    @extract_exception
    def get_stats_for_mgs(self,request,mds_name,start_time,end_time ,data_function,fetch_metrics):
            return ''
