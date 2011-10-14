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
        AnonymousRequestHandler.__init__(self,self.get_fs_stats_for_targets)

    @classmethod
    @extract_request_args(filesystem_name='filesystem',start_time='starttime',end_time='endtime',data_function='datafunction',target_kind='targetkind',fetch_metrics='fetchmetrics')
    @extract_exception
    def get_fs_stats_for_targets(self,request,filesystem_name,start_time,end_time ,data_function,target_kind,fetch_metrics):
        assert target_kind in ['OST', 'MDT']
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
    def metrics_fetch(self,fs,target_kind,fetch_metrics,start_time,end_time,interval,datafunction='Average'):
        import time
        if target_kind == 'OST':
            if interval:
                if fetch_metrics:
                    fs_target_stats = fs.metrics.fetch(datafunction,ObjectStoreTarget,fetch_metrics=fetch_metrics.split(),start_time=int(time.time()-600))
                else:
                    fs_target_stats = fs.metrics.fetch(datafunction,ObjectStoreTarget,start_time=int(time.time()-600))
            elif start_time:
                if fetch_metrics:
                    fs_target_stats = fs.metrics.fetch(datafunction,ObjectStoreTarget,fetch_metrics=fetch_metrics.split(),start_time=int(time.time()-600))
                else:
                    fs_target_stats = fs.metrics.fetch(datafunction,ObjectStoreTarget,start_time=int(time.time()-600))
            else:
                if fetch_metrics:
                    fs_target_stats = fs.metrics.fetch_last(ObjectStoreTarget,fetch_metrics=fetch_metrics.split())
                else:
                    fs_target_stats = fs.metrics.fetch_last(ObjectStoreTarget)
        elif target_kind == 'MDT':
            if interval:
                if fetch_metrics:
                    fs_target_stats = fs.metrics.fetch(datafunction,MetadataTarget,fetch_metrics=fetch_metrics.split(),start_time=int(time.time()-600))
                else:
                    fs_target_stats = fs.metrics.fetch(datafunction,MetadataTarget,start_time=int(time.time()-600))
            elif start_time:
                if fetch_metrics:
                    fs_target_stats = fs.metrics.fetch(datafunction,MetadataTarget,fetch_metrics=fetch_metrics.split(),start_time=int(time.time()-600))
                else:
                    fs_target_stats = fs.metrics.fetch(datafunction,MetadataTarget,start_time=int(time.time()-600))
            else:
                if fetch_metrics:
                    fs_target_stats = fs.metrics.fetch_last(MetadataTarget,fetch_metrics=fetch_metrics.split())
                else:
                    fs_target_stats = fs.metrics.fetch_last(MetadataTarget)   
        else:
            if interval:
                if fetch_metrics:
                    fs_target_stats = fs.metrics.fetch(datafunction,fetch_metrics=fetch_metrics.split(),start_time=int(time.time()-600))
                else:
                    fs_target_stats = fs.metrics.fetch(datafunction,start_time=int(time.time()-600))
            elif start_time:
                if fetch_metrics:
                    fs_target_stats = fs.metrics.fetch(datafunction,fetch_metrics=fetch_metrics.split(),start_time=int(time.time()-600))
                else:
                    fs_target_stats = fs.metrics.fetch(datafunction,start_time=int(time.time()-600))
            else:
                if fetch_metrics:
                    fs_target_stats = fs.metrics.fetch_last(fetch_metrics=fetch_metrics.split())
                else:
                    fs_target_stats = fs.metrics.fetch_last()
        return fs_target_stats

class GetFSServerStats(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_fs_stats_for_server)

    @classmethod
    @extract_request_args(filesystem_name='filesystem',start_time='starttime',end_time='endtime' ,data_function='datafunction',fetch_metrics='fetchmetrics')
    @extract_exception
    def get_fs_stats_for_server(self,request,filesystem_name,start_time,end_time ,data_function,fetch_metrics):
        interval = 600
        if filesystem_name:
            host_stats_metric = []
            fs = Filesystem.objects.get(name=filesystem_name)
            hosts = fs.get_servers()
            for host in hosts:
                host_stats_metric.append(self.metrics_fetch(host,fetch_metrics,start_time,end_time,interval))
            return host_stats_metric
        else:
            all_host_stats_metrics = []
            for fs in Filesystem.objects.all():
                hosts = fs.get_servers()
                host_stats_metric = []  
                for host in Host.objects.all():
                    host_stats_metric.append(self.metrics_fetch(host,fetch_metrics,start_time,end_time,interval))
                all_host_stats_metrics.extend(host_stats_metric.append)  
            return all_host_stats_metrics

    @classmethod
    @extract_exception
    def metrics_fetch(self,host,fetch_metrics,start_time,end_time,interval,datafunction='Average'):
        import time
        if interval:
            if fetch_metrics:
                host_stats = host.metrics.fetch(datafunction,fetch_metrics=fetch_metrics.split(),start_time=int(time.time()-600))
            else:
                host_stats = host.metrics.fetch(datafunction,start_time=int(time.time()-600))
        elif start_time:
            if fetch_metrics:
                host_stats = host.metrics.fetch(datafunction,fetch_metrics=fetch_metrics.split(),start_time=int(time.time()-600))
            else:
                host_stats = host.metrics.fetch(datafunction,start_time=int(time.time()-600))
        else:
            if fetch_metrics:
                host_stats = host.metrics.fetch_last(fetch_metrics=fetch_metrics.split())
            else:
                host_stats = host.metrics.fetch_last()
        return host_stats

class GetFSMGSStats(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_fs_stats_for_mgs)

    @classmethod
    @extract_request_args(filesystem_name='filesystem',start_time='starttime',end_time='endtime' ,data_function='datafunction',fetch_metrics='fetchmetrics')
    @extract_exception
    def get_fs_stats_for_mgs(self,request,filesystem_name,start_time,end_time ,data_function,fetch_metrics):
        interval = 600
        if filesystem_name:
            mgs_stats_metric = []
            fs = Filesystem.objects.get(name=filesystem_name)
            mgs = fs.mgs
            mgs_stats_metric.append(self.metrics_fetch(mgs,fetch_metrics,start_time,end_time,interval))
            return mgs_stats_metric
        else:
            all_mgs_stats_metric = []
            for fs in Filesystem.objects.all():
                mgs = fs.mgs
                all_mgs_stats_metric.append(self.metrics_fetch(mgs,fetch_metrics,start_time,end_time,interval))
            return all_mgs_stats_metric

    @classmethod
    @extract_exception
    def metrics_fetch(self,mgs,fetch_metrics,start_time,end_time,interval,datafunction='Average'):
        import time
        if interval:
            if fetch_metrics:
                mgs_stats = mgs.metrics.fetch(datafunction,fetch_metrics=fetch_metrics.split(),start_time=int(time.time()-600))
            else:
                mgs_stats = mgs.metrics.fetch(datafunction,start_time=int(time.time()-600))
        elif start_time:
            if fetch_metrics:
                mgs_stats = mgs.metrics.fetch(datafunction,fetch_metrics=fetch_metrics.split(),start_time=int(time.time()-600))
            else:
                mgs_stats = mgs.metrics.fetch(datafunction,start_time=int(time.time()-600))
        else:
            if fetch_metrics:
                mgs_stats = mgs.metrics.fetch_last(fetch_metrics=fetch_metrics.split())
            else:
                mgs_stats = mgs.metrics.fetch_last()
        return mgs_stats

class GetServerStats(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_stats_for_server)

    @classmethod
    @extract_request_args(host_id='hostid',start_time='starttime',end_time='endtime' ,data_function='datafunction',fetch_metrics='fetchmetrics')
    @extract_exception
    def get_stats_for_server(self,request,host_id,start_time,end_time ,data_function,fetch_metrics):
        interval = 600
        if host_id:
            host = Host.objects.get(id=host_id)
            return self.metrics_fetch(host,fetch_metrics,start_time,end_time,interval)
        else:
            raise Exception("Unable to find host with hostid=%s" %host_id)

    @classmethod
    @extract_exception
    def metrics_fetch(self,host,fetch_metrics,start_time,end_time,interval,datafunction='Average'):
        import time
        if interval:
            if fetch_metrics:
                host_stats = host.metrics.fetch(datafunction,fetch_metrics=fetch_metrics.split(),start_time=int(time.time()-600))
            else:
                host_stats = host.metrics.fetch(datafunction,start_time=int(time.time()-600))
        elif start_time:
            if fetch_metrics:
                host_stats = host.metrics.fetch(datafunction,fetch_metrics=fetch_metrics.split(),start_time=int(time.time()-600))
            else:
                host_stats = host.metrics.fetch(datafunction,start_time=int(time.time()-600))
        else:
            if fetch_metrics:
                host_stats = host.metrics.fetch_last(fetch_metrics=fetch_metrics.split())
            else:
                host_stats = host.metrics.fetch_last()
        return host_stats

class GetTargetStats(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_stats_for_targets)

    @classmethod
    @extract_request_args(target_name='target',start_time='starttime',end_time='endtime',data_function='datafunction',target_kind='targetkind',fetch_metrics='fetchmetrics')
    @extract_exception
    def get_stats_for_targets(self,request,target_name,start_time,end_time ,data_function,target_kind,fetch_metrics):
        assert target_kind in ['OST', 'MDT']
        interval=600
        if target_kind == 'OST':
            target = ObjectStoreTarget.objects.get(id=target_name)
            return self.metrics_fetch(target,fetch_metrics,start_time,end_time,interval)
        elif target_kind == 'MDT':
            target = MetadataTarget.ojbects.get(id=target_name)
            return self.metrics_fetch(target,fetch_metrics,start_time,end_time,interval)

    @classmethod
    @extract_exception
    def metrics_fetch(self,target,fetch_metrics,start_time,end_time,interval,datafunction='Average'):
        import time
        if interval:
            if fetch_metrics:
                target_stats = target.metrics.fetch(datafunction,ObjectStoreTarget,fetch_metrics=fetch_metrics.split(),start_time=int(time.time()-600))
            else:
                target_stats = target.metrics.fetch(datafunction,ObjectStoreTarget,start_time=int(time.time()-600))
        elif start_time:
            if fetch_metrics:
                target_stats = target.metrics.fetch(datafunction,ObjectStoreTarget,fetch_metrics=fetch_metrics.split(),start_time=int(time.time()-600))
            else:
                target_stats = target.metrics.fetch(datafunction,ObjectStoreTarget,start_time=int(time.time()-600))
        else:
            if fetch_metrics:
                target_stats = target.metrics.fetch_last(ObjectStoreTarget,fetch_metrics=fetch_metrics.split())
            else:
                target_stats = target.metrics.fetch_last(ObjectStoreTarget)
        return target_stats

class GetFSClientsStats(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_fs_stats_for_client)

    @classmethod
    @extract_request_args(filesystem_name='filesystem',start_time='starttime',end_time='endtime' ,data_function='datafunction',fetch_metrics='fetchmetrics')
    @extract_exception
    def get_fs_stats_for_client(self,request,filesystem_name,start_time,end_time ,data_function,fetch_metrics):
         return ''
