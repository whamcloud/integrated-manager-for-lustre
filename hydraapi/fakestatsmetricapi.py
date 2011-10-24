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
                            Host)

class GetFSTargetStats_fake(AnonymousRequestHandler):
    @extract_request_args('filesystem','starttime','endtime','datafunction','targetkind','fetchmetrics')
    def run(self,request,filesystem,starttime,endtime ,datafunction,targetkind,fetchmetrics):
        assert targetkind in ['OST', 'MDT']
        from random import randrange,uniform
        if fetchmetrics == "kbytestotal kbytesfree filestotal filesfree":
            if filesystem:
                return [
                        {
                         'timestamp' : '1316847600',
                         'filesystem' : filesystem,
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
        elif fetchmetrics == "stats_read_bytes stats_write_bytes":
            if filesystem:
                current_slice = gettimeslice()
                
                return [
                        {
                         'timestamp' : slice,
                         'filesystem' : filesystem,
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
        elif fetchmetrics == "iops1 iops2 iops3 iops4 iops5":
            if filesystem:
                current_slice = gettimeslice()

                return [
                        {
                         'timestamp' : slice,
                         'filesystem' : filesystem,
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
    @extract_request_args('filesystem','starttime','endtime' ,'datafunction','fetchmetrics')
    def run(self,request,filesystem,starttime,endtime ,datafunction,fetchmetrics):
        from  random import randrange
        data_slice = []
        current_slice = gettimeslice()
        if filesystem:
            host_stats_metric = []
            fs = Filesystem.objects.get(name=filesystem)
            hosts = fs.get_servers()
            for host in hosts:
                for slice in current_slice:
                    data_slice.append(
                                      {
                                       'timestamp': slice,
                                       'host' : host.address,
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
                                                  'host' : host.address,
                                                  'mem_MemFree' : randrange(1024,16384,3),
                                                  'mem_MemTotal':'16384',
                                                  'cpu_usage' : randrange(0,100,3),
                                                  'cpu_total' : '100',
                                                 }
                                                )
            return host_stats_metric

class GetServerStats_fake(AnonymousRequestHandler):
    @extract_request_args('hostid','starttime','endtime' ,'datafunction','fetchmetrics')
    def run(self,request,hostid,starttime,endtime ,datafunction,fetchmetrics):
        from  random import randrange
        data_slice = []
        current_slice = gettimeslice()
        if hostid:
            host = Host.objects.get(id=hostid)
            for slice in current_slice:
                    data_slice.append(
                                      {
                                       'timestamp': slice,
                                       'host' : host.address,
                                       'mem_MemFree' : randrange(1024,16384,3),
                                       'mem_MemTotal':'16384',
                                       'cpu_usage' : randrange(0,100,3),
                                       'cpu_total' : '100',        
                                      }
                                     )
            return data_slice
        else:
            raise Exception("Unable to find host with hostid=%s" %hostid)

class GetTargetStats_fake(AnonymousRequestHandler):
    @extract_request_args('target','starttime','endtime','datafunction','targetkind','fetchmetrics')
    def run(self,request,target,starttime,endtime ,datafunction,targetkind,fetchmetrics):
        assert targetkind in ['OST', 'MDT']
        from random import randrange,uniform
        if fetchmetrics == "kbytestotal kbytesfree filestotal filesfree":
            return [
                    {
                     'timestamp' : '1316847600',
                     'filesystem' : target,
                     'kbytesfree' : uniform(0,4940388537.9860001),
                     'kbytestotal': '4940834834.4740801',
                     'filesfree' : randrange(0,4940388537,3),
                     'filestotal': '4940834834',
                    }
            ]
        elif fetchmetrics == "stats_read_bytes stats_write_bytes":
            current_slice = gettimeslice()
            return [
                    {
                     'timestamp' : slice,
                     'filesystem' : target,
                     'stats_read_bytes' : randrange(0,4940388537,10),
                     'stats_write_bytes': randrange(0,4940388537,10),
                    }
                    for slice in current_slice
            ]
        elif fetchmetrics == "iops1 iops2 iops3 iops4 iops5":
            return [
                    {
                     'timestamp' : slice,
                     'filesystem' : target,
                     'iops1' : randrange(0,4940388537,3),
                     'iops2' : randrange(0,5940388537,3),
                     'iops3' : randrange(0,6940388537,3),
                     'iops4' : randrange(0,3940388537,3),
                     'iops5' : randrange(0,1940388537,3), 
                    }
                    for slice in current_slice
            ]


class GetFSClientsStats_fake(AnonymousRequestHandler):
    @extract_request_args('filesystem','starttime','endtime' ,'datafunction','fetchmetrics')
    def run(self,request,filesystem,starttime,endtime ,datafunction,fetchmetrics):
         from random import randrange
         current_slice = gettimeslice()
         return [
                {
                 'timestamp' : slice,
                 'filesystem' : filesystem,
                 'num_exports' : randrange(0,137,3),
                }
                for slice in current_slice
         ]


class GetFSMGSStats(AnonymousRequestHandler):
    @extract_request_args('filesystem','starttime','endtime','datafunction','fetchmetrics')
    def run(self,request,filesystem,starttime,endtime ,datafunction,fetchmetrics):
        return ''


class GetFSOSTHeatMap(AnonymousRequestHandler):
    @extract_request_args('filesystem','starttime','endtime' ,'datafunction','fetchmetrics')
    def run(self,request,filesystem,starttime,endtime ,datafunction,fetchmetrics):
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
                          'filesystem' : filesystem,
                          'ost': ost_name,
                          'color':self.getcolor(cpu),
                          fetchmetrics : cpu,
                         }
                        )
         return ost_data   
    
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
