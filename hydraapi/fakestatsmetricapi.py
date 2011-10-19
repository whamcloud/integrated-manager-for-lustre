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
                            Host)

class GetFSTargetStats_fake(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_fs_stats_for_targets_fake)

    @classmethod
    @extract_request_args(filesystem_name='filesystem',start_time='starttime',end_time='endtime',data_function='datafunction',target_kind='targetkind',fetch_metrics='fetchmetrics')
    @extract_exception
    def get_fs_stats_for_targets_fake(self,request,filesystem_name,start_time,end_time ,data_function,target_kind,fetch_metrics):
        assert target_kind in ['OST', 'MDT']
        from random import randrange,uniform
        if fetch_metrics == "kbytestotal kbytesfree filestotal filesfree":
            if filesystem_name:
                return [
                        {
                         'timestamp' : '1316847600',
                         'filesystem' : filesystem_name,
                         'kbytesfree' : uniform(0,4940388537.9860001),
                         'kbytestotal': '4940834834.4740801',
                         'filesfree' : randrange(0,4940388537,3),
                         'filestotal': '4940834834',
                        }
                ]
            else:
                return [
                        {
                         'timestamp' : '1316847600',
                         'filesystem' : filesystem.name,
                         'kbytesfree' : uniform(0,4940388537.9860001),
                         'kbytestotal': '4940834834.4740801',
                         'filesfree' : randrange(0,4940388537,10),
                         'filestotal': randrange(0,4940388537,10),
                        }
                        for filesystem in Filesystem.objects.all()
                ]
        elif fetch_metrics == "stats_read_bytes stats_write_bytes":
            if filesystem_name:
                current_slice = gettimeslice()
                
                return [
                        {
                         'timestamp' : slice,
                         'filesystem' : filesystem_name,
                         'stats_read_bytes' : randrange(0,4940388537,10),
                         'stats_write_bytes': randrange(0,4940388537,10),
                        }
                        for slice in current_slice
                ]
            else:
                all_fs_stats=[]
                fs_stats=[]
                current_slice = gettimeslice()
                for filesystem in Filesystem.objects.all():
                    for slice in current_slice:
                        fs_stats.append(    
                                        {
                                         'timestamp' : slice,
                                         'filesystem' : filesystem.name,
                                         'stats_read_bytes' : randrange(0,4940388537,10),
                                         'stats_write_bytes': randrange(0,4940388537,10),
                                        }
                                       ) 
                    all_fs_stats.extend(fs_stats)
                return all_fs_stats
        elif fetch_metrics == "iops1 iops2 iops3 iops4 iops5":
            if filesystem_name:
                current_slice = gettimeslice()

                return [
                        {
                         'timestamp' : slice,
                         'filesystem' : filesystem_name,
                         'iops1' : randrange(0,4940388537,3),
                         'iops2' : randrange(0,5940388537,3),
                         'iops3' : randrange(0,6940388537,3),
                         'iops4' : randrange(0,3940388537,3),
                         'iops5' : randrange(0,1940388537,3), 
                        }
                        for slice in current_slice
                ]
            else:
                all_fs_stats=[]
                fs_stats=[]
                current_slice = gettimeslice()
                for filesystem in Filesystem.objects.all():
                    for slice in current_slice:
                        fs_stats.append(
                                        {
                                         'timestamp' : slice,
                                         'filesystem' : filesystem.name,
                                         'iops1' : randrange(0,4940388537,3),
                                         'iops2' : randrange(0,5940388537,3),
                                         'iops3' : randrange(0,6940388537,3),
                                         'iops4' : randrange(0,3940388537,3),
                                         'iops5' : randrange(0,1940388537,3),
                                        }
                                       )
                    all_fs_stats.extend(fs_stats)
                return all_fs_stats


class GetFSServerStats_fake(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_fs_stats_for_server_fake)

    @classmethod
    @extract_request_args(filesystem_name='filesystem',start_time='starttime',end_time='endtime' ,data_function='datafunction',fetch_metrics='fetchmetrics')
    @extract_exception
    def get_fs_stats_for_server_fake(self,request,filesystem_name,start_time,end_time ,data_function,fetch_metrics):
        from  random import randrange
        data_slice = []
        current_slice = gettimeslice()
        if filesystem_name:
            host_stats_metric = []
            fs = Filesystem.objects.get(name=filesystem_name)
            hosts = fs.get_servers()
            for host in hosts:
                for slice in current_slice:
                    data_slice.append(
                                      {
                                       'timestamp': slice,
                                       'hostname' : host.address,
                                       'mem_MemFree' : randrange(1024,16384,3),
                                       'mem_MemTotal':'16384',
                                       'cpu_usage' : randrange(0,100,3),
                                       'cpu_total' : '100',
                                      }
                                     )
                return data_slice
        else:
            for fs in Filesystem.objects.all():
                hosts = fs.get_servers()
                host_stats_metric = []  
                for host in Host.objects.all():
                    current_slice = gettimeslice() 
                    host_stats_metric = []            
                    for slice in current_slice:
                        host_stats_metric.append(
                                                 {
                                                  'timestamp': slice,
                                                  'hostname' : host.address,
                                                  'mem_MemFree' : randrange(1024,16384,3),
                                                  'mem_MemTotal':'16384',
                                                  'cpu_usage' : randrange(0,100,3),
                                                  'cpu_total' : '100',
                                                 }
                                                )
            return host_stats_metric

class GetServerStats_fake(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_stats_for_server_fake)

    @classmethod
    @extract_request_args(host_id='hostid',start_time='starttime',end_time='endtime' ,data_function='datafunction',fetch_metrics='fetchmetrics')
    @extract_exception
    def get_stats_for_server_fake(self,request,host_id,start_time,end_time ,data_function,fetch_metrics):
        from  random import randrange
        data_slice = []
        current_slice = gettimeslice()
        if host_id:
            host = Host.objects.get(id=host_id)
            for slice in current_slice:
                    data_slice.append(
                                      {
                                       'timestamp': slice,
                                       'hostname' : host.address,
                                       'mem_MemFree' : randrange(1024,16384,3),
                                       'mem_MemTotal':'16384',
                                       'cpu_usage' : randrange(0,100,3),
                                       'cpu_total' : '100',        
                                      }
                                     )
            return data_slice
        else:
            raise Exception("Unable to find host with hostid=%s" %host_id)

class GetTargetStats_fake(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_stats_for_targets_fake)

    @classmethod
    @extract_request_args(target_name='target',start_time='starttime',end_time='endtime',data_function='datafunction',target_kind='targetkind',fetch_metrics='fetchmetrics')
    @extract_exception
    def get_stats_for_targets_fake(self,request,target_name,start_time,end_time ,data_function,target_kind,fetch_metrics):
        assert target_kind in ['OST', 'MDT']
        from random import randrange,uniform
        if fetch_metrics == "kbytestotal kbytesfree filestotal filesfree":
            return [
                    {
                     'timestamp' : '1316847600',
                     'filesystem' : target_name,
                     'kbytesfree' : uniform(0,4940388537.9860001),
                     'kbytestotal': '4940834834.4740801',
                     'filesfree' : randrange(0,4940388537,3),
                     'filestotal': '4940834834',
                    }
            ]
        elif fetch_metrics == "stats_read_bytes stats_write_bytes":
            current_slice = gettimeslice()
            return [
                    {
                     'timestamp' : slice,
                     'filesystem' : target_name,
                     'stats_read_bytes' : randrange(0,4940388537,10),
                     'stats_write_bytes': randrange(0,4940388537,10),
                    }
                    for slice in current_slice
            ]
        elif fetch_metrics == "iops1 iops2 iops3 iops4 iops5":
            return [
                    {
                     'timestamp' : slice,
                     'filesystem' : target_name,
                     'iops1' : randrange(0,4940388537,3),
                     'iops2' : randrange(0,5940388537,3),
                     'iops3' : randrange(0,6940388537,3),
                     'iops4' : randrange(0,3940388537,3),
                     'iops5' : randrange(0,1940388537,3), 
                    }
                    for slice in current_slice
            ]


class GetFSClientsStats_fake(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_fs_stats_for_client_fake)

    @classmethod
    @extract_request_args(filesystem_name='filesystem',start_time='starttime',end_time='endtime' ,data_function='datafunction',fetch_metrics='fetchmetrics')
    @extract_exception
    def get_fs_stats_for_client_fake(self,request,filesystem_name,start_time,end_time ,data_function,fetch_metrics):
         from random import randrange
         current_slice = gettimeslice()
         return [
                {
                 'timestamp' : slice,
                 'filesystem' : filesystem_name,
                 'clients_mounts' : randrange(0,137,3),
                }
                for slice in current_slice
         ]


class GetFSMGSStats(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_fs_stats_for_mgs)

    @classmethod
    @extract_request_args(filesystem_name='filesystem',start_time='starttime',end_time='endtime' ,data_function='datafunction',fetch_metrics='fetchmetrics')
    @extract_exception
    def get_fs_stats_for_mgs(self,request,filesystem_name,start_time,end_time ,data_function,fetch_metrics):
        return ''


class GetFSOSTHeatMap(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_fs_ost_heatmap)

    @classmethod
    @extract_request_args(filesystem_name='filesystem',start_time='starttime',end_time='endtime' ,data_function='datafunction',fetch_metrics='fetchmetrics')
    @extract_exception
    def get_fs_ost_heatmap(self,request,filesystem_name,start_time,end_time ,data_function,fetch_metrics):
         from random import randrange
         ost_data = []
         ost_size=100
         current_slice = gettimeslice(100,5)
         for i in xrange(ost_size):
             for slice in current_slice:
                ost_name='ost' + str(i)  
                cpu = randrange(0,100,1)
                ost_data.append(
                         {
                          'timestamp' : slice,
                          'filesystem' : filesystem_name,
                          'ost': ost_name,
                          'color':self.getcolor(cpu),
                          fetch_metrics : cpu,
                         }
                        )
         return ost_data   
    
    @classmethod 
    def getcolor(self,cpu):
       if cpu <= 25:
            return '#00ff00'
       elif cpu <=50:
            return '#001f00'
       elif cpu <=75:
            return '#ffff00'
       elif cpu <=100:
            return '#ff0000' 

def gettimeslice(sample_size=10,interval=5):
    from datetime import timedelta,datetime
    current_time = datetime.now()
    data_slice = []
    for i in xrange(sample_size):
        current_time  = current_time - timedelta(seconds=interval)
        strtime  = current_time.isoformat().split('T')[1]
        data_slice.append(strtime.split('.')[0])
    return data_slice
