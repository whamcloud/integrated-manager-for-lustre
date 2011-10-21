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
                            extract_request_args)
from monitor.models import (Filesystem,
                            MetadataTarget,
                            ObjectStoreTarget,
                            Host)
#Fix Me:
#Note that these integer-based queries will go away soon. 
#Planning to land changes to the metrics API which allow datetime objects to be used instead of requiring integers
#That's why all APIs have start and end time for now only start_time is used for passing the last number of minutes for data fetch

class GetFSTargetStats(AnonymousRequestHandler):
    @extract_request_args('filesystem','starttime','endtime','datafunction','targetkind','fetchmetrics')
    def run(self,request,filesystem,starttime,endtime ,datafunction,targetkind,fetchmetrics):
        assert targetkind in ['OST', 'MDT']
        interval='' 
        if filesystem:
            fs = Filesystem.objects.get(name=filesystem)
            return self.metrics_fetch(fs,targetkind,fetchmetrics,starttime,endtime,interval)
        else:
            all_fs_stats = []
            for fs in Filesystem.objects.all():
                all_fs_stats.extend(self.metrics_fetch(fs,targetkind,fetchmetrics,starttime,endtime,interval))
            return all_fs_stats

    def metrics_fetch(self,fs,target_kind,fetch_metrics,start_time,end_time,interval,datafunction='Average'):
        if target_kind == 'OST':
            if start_time:
                start_time = int(start_time)
                start_time = getstartdate(start_time)
                if fetch_metrics:
                    fs_target_stats = fs.metrics.fetch(datafunction,ObjectStoreTarget,fetch_metrics=fetch_metrics.split(),start_time=start_time)
                else:
                    fs_target_stats = fs.metrics.fetch(datafunction,ObjectStoreTarget,start_time=start_time)
            else:
                if fetch_metrics:
                    fs_target_stats = fs.metrics.fetch_last(ObjectStoreTarget,fetch_metrics=fetch_metrics.split())
                else:
                    fs_target_stats = fs.metrics.fetch_last(ObjectStoreTarget)
        elif target_kind == 'MDT':
            if start_time:
                start_time = int(start_time)
                start_time = getstartdate(start_time)
                if fetch_metrics:
                    fs_target_stats = fs.metrics.fetch(datafunction,MetadataTarget,fetch_metrics=fetch_metrics.split(),start_time=start_time)
                else:
                    fs_target_stats = fs.metrics.fetch(datafunction,MetadataTarget,start_time=start_time)
            else:
                if fetch_metrics:
                    fs_target_stats = fs.metrics.fetch_last(MetadataTarget,fetch_metrics=fetch_metrics.split())
                else:
                    fs_target_stats = fs.metrics.fetch_last(MetadataTarget)   
        anystats = []
        if fs_target_stats:
            if start_time:  
                for stats_data in fs_target_stats:
                    stats_data[1]['filesystem'] = fs.name
                    stats_data[1]['timestamp'] = stats_data[0]
                    anystats.append(stats_data[1])
            else:
                fs_target_stats[1]['filesystem'] = fs.name
                fs_target_stats[1]['timestamp'] = fs_target_stats[0]
                anystats.append(fs_target_stats[1])
        return anystats

class GetFSServerStats(AnonymousRequestHandler):
    @extract_request_args('filesystem','starttime','endtime','datafunction','fetchmetrics')
    def run(self,request,filesystem,starttime,endtime ,datafunction,fetchmetrics):
        interval =''
        if filesystem:
            host_stats_metric = []
            fs = Filesystem.objects.get(name=filesystem)
            hosts = fs.get_servers()
            for host in hosts:
                host_stats_metric.extend(self.metrics_fetch(host,fetchmetrics,starttime,endtime,interval))
            return host_stats_metric
        else:
            for fs in Filesystem.objects.all():
                hosts = fs.get_servers()
                host_stats_metric = []  
                for host in hosts:
                    host_stats_metric.extend(self.metrics_fetch(host,fetchmetrics,starttime,endtime,interval))
            return host_stats_metric

    def metrics_fetch(self,host,fetch_metrics,start_time,end_time,interval,datafunction='Average'):
        if start_time:
            start_time = int(start_time)
            start_time = getstartdate(start_time)
            if fetch_metrics:
                host_stats = host.metrics.fetch(datafunction,fetch_metrics=fetch_metrics.split(),start_time=start_time)
            else:
                host_stats = host.metrics.fetch(datafunction,start_time=start_time)
        else:
            if fetch_metrics:
                host_stats = host.metrics.fetch_last(fetch_metrics=fetch_metrics.split())
            else:
                host_stats = host.metrics.fetch_last()
        onlystats = []   
        if host_stats:
            if start_time:
                for stats_data in host_stats:
                    stats_data[1]['host'] = host.address
                    stats_data[1]['timestamp'] = stats_data[0]
                    onlystats.append(stats_data[1])      
            else:
                host_stats[1]['host'] = host.address
                host_stats[1]['timestamp'] = host_stats[0]
                onlystats.append(host_stats[1]) 
        return onlystats

class GetFSMGSStats(AnonymousRequestHandler):
    @extract_request_args('filesystem','starttime','endtime' ,'datafunction','fetchmetrics')
    def run(self,request,filesystem,starttime,endtime ,datafunction,fetchmetrics):
        interval =''
        if filesystem:
            mgs_stats_metric = []
            fs = Filesystem.objects.get(name=filesystem)
            mgs = fs.mgs
            mgs_stats_metric.append(self.metrics_fetch(mgs,fetchmetrics,starttime,endtime,interval))
            return mgs_stats_metric
        else:
            all_mgs_stats_metric = []
            for fs in Filesystem.objects.all():
                mgs = fs.mgs
                all_mgs_stats_metric.extend(self.metrics_fetch(mgs,fetchmetrics,starttime,endtime,interval))
            return all_mgs_stats_metric

    def metrics_fetch(self,mgs,fetch_metrics,start_time,end_time,interval,datafunction='Average'):
        if start_time:
            start_time = int(start_time)
            start_time = getstartdate(start_time)
            if fetch_metrics:
                mgs_stats = mgs.metrics.fetch(datafunction,fetch_metrics=fetch_metrics.split(),start_time=start_time)
            else:
                mgs_stats = mgs.metrics.fetch(datafunction,start_time=start_time)
        else:
            if fetch_metrics:
                mgs_stats = mgs.metrics.fetch_last(fetch_metrics=fetch_metrics.split())
            else:
                mgs_stats = mgs.metrics.fetch_last()
        if mgs_stats:
            if start_time:
                for stats_data in mgs_stats:
                    stats_data[1]['host'] = mgs.name
                    stats_data[1]['timestamp'] = stats_data[0]
            else:
                mgs_stats[1]['host'] = mgs.name
                mgs_stats[1]['timestamp'] = mgs_stats[0]
        return mgs_stats

class GetServerStats(AnonymousRequestHandler):
    @extract_request_args('hostid','starttime','endtime' ,'datafunction','fetchmetrics')
    def run(self,request,hostid,starttime,endtime ,datafunction,fetchmetrics):
        interval =''
        if hostid:
            host = Host.objects.get(id=hostid)
            return self.metrics_fetch(host,fetchmetrics,starttime,endtime,interval)
        else:
            raise Exception("Unable to find host with hostid=%s" %hostid)

    def metrics_fetch(self,host,fetch_metrics,start_time,end_time,interval,datafunction='Average'):
        if start_time:
            start_time = int(start_time)
            start_time = getstartdate(start_time)
            if fetch_metrics:
                host_stats = host.metrics.fetch(datafunction,fetch_metrics=fetch_metrics.split(),start_time=start_time)
            else:
                host_stats = host.metrics.fetch(datafunction,start_time=start_time)
        else:
            if fetch_metrics:
                host_stats = host.metrics.fetch_last(fetch_metrics=fetch_metrics.split())
            else:
                host_stats = host.metrics.fetch_last()
        if host_stats:
            if start_time:
                for stats_data in host_stats:
                    stats_data[1]['host'] = host.address
                    stats_data[1]['timestamp'] = stats_data[0]
            else:
                host_stats[1]['host'] = host.address
                host_stats[1]['timestamp'] = host_stats[0]
        return host_stats

class GetTargetStats(AnonymousRequestHandler):
    @extract_request_args('target','starttime','endtime','datafunction','targetkind','fetchmetrics')
    def run(self,request,target,starttime,endtime ,datafunction,targetkind,fetchmetrics):
        assert targetkind in ['OST', 'MDT']
        interval=''
        if targetkind == 'OST':
            target = ObjectStoreTarget.objects.get(name=target)
            return self.metrics_fetch(target,fetchmetrics,starttime,endtime,interval)
        elif targetkind == 'MDT':
            target = MetadataTarget.objects.get(name=target)
            return self.metrics_fetch(target,fetchmetrics,starttime,endtime,interval)

    def metrics_fetch(self,target,fetch_metrics,start_time,end_time,interval,datafunction='Average'):
        if start_time:
            start_time = int(start_time)
            start_time = getstartdate(start_time)
            if fetch_metrics:
                target_stats = target.metrics.fetch(datafunction,fetch_metrics=fetch_metrics.split(),start_time=start_time)
            else:
                target_stats = target.metrics.fetch(datafunction,start_time=start_time)
        else:
            if fetch_metrics:
                target_stats = target.metrics.fetch_last(fetch_metrics=fetch_metrics.split())
            else:
                target_stats = target.metrics.fetch_last()
        if target_stats:
            if start_time:
                start_time=int(start_time)
                start_time = getstartdate(start_time)             
                for stats_data in target_stats:
                    stats_data[1]['target'] = target.name
            else:
                target_stats[1]['target'] = target.name
                target_stats[1]['timestamp'] = target_stats[0]
        return target_stats

class GetFSClientsStats(AnonymousRequestHandler):
    @extract_request_args('filesystem','starttime','endtime' ,'datafunction','fetchmetrics')
    def run(self,request,filesystem,starttime,endtime ,datafunction,fetchmetrics):
        interval=''
        client_stats = []
        if filesystem:
            fs = Filesystem.objects.get(name=filesystem)    
            return self.metrics_fetch(fs,starttime,endtime,interval) 
        else:
            for fs in Filesystem.objects.all():
                client_stats.extend(self.metrics_fetch(fs,starttime,endtime,interval)) 
            return client_stats

    def metrics_fetch(self,filesystem,start_time,end_time,interval,datafunction='Average'):
        fetch_metrics="num_exports"
        client_stats = [] 
        if start_time:
            start_time = int(start_time)
            start_time = getstartdate(start_time)  
            client_stats = filesystem.metrics.fetch(datafunction,ObjectStoreTarget,fetch_metrics=fetch_metrics.split(),start_time=start_time)
        else:
            try:
                client_stats = filesystem.metrics.fetch_last(ObjectStoreTarget,fetch_metrics=fetch_metrics.split())
            except:
                pass
        onlystats = [] 
        if client_stats:
            if start_time:
                for stats_data in client_stats:
                    stats_data[1]['filesystem'] = filesystem.name
                    stats_data[1]['timestamp'] = stats_data[0]
                    onlystats.append(stats_data[1])       
            else:
                client_stats[1]['filesystem'] = filesystem.name
                client_stats[1]['timestamp'] = client_stats[0]
                onlystats.append(client_stats[1])
        return onlystats

def getstartdate(start_time):
    import datetime
    now = lambda: datetime.datetime.now()
    minutes = datetime.timedelta(minutes=1)
    startdatetime = (now() - minutes * int(start_time)).isoformat()
    return _str2dt(startdatetime)

def _str2dt(in_string):
    """Parse a string and return a datetime object."""
    import dateutil.parser
    return dateutil.parser.parse(in_string)
