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
                            ManagementTarget,
                            ObjectStoreTarget,
                            Client,
                            Host,
                            SshMonitor)

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

#
class ListFileSystems(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.list_filesystems)

    @classmethod
    def list_filesystems(self,request):
        try:
            return [
                    {
                     'id' : filesystem.id,
                     'name': filesystem.name,
                     'status' : filesystem.status_string()
                    } 
                    for filesystem in Filesystem.objects.all()
            ]
        except:
            raise Exception('GET call API_Exception:list_filesystem() => Failed to get the list of File systems')

class GetFileSystem(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_filesystem)

    @classmethod
    @extract_request_args(filesystem_name='filesystem')
    def get_filesystem(self,request,filesystem_name):
        try:    
            if filesystem_name:
                filesystem = Filesystem.objects.get(name = filesystem_name)
                return {             
                        'id' : filesystem.id,
                        'name': filesystem.name,
                        'status' : filesystem.status_string()
                       }
            else:
                return {'id' : 'filesystem not found'}
        except:
            raise Exception('POST call API_Exception:get_filesystem(filesystem_name) => Failed to get the filesystem=%s' %filesystem_name)

class GetVolumes(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
       AnonymousRequestHandler.__init__(self,self.get_volumes)

    @classmethod
    @extract_request_args(filesystem_name='filesystem')
    def get_volumes(self,request,filesystem_name):
        try:
            if filesystem_name:
                return self.get_volumes_per_fs(Filesystem.objects.get(name = filesystem_name))
            else:
                volumes_list = []
                for fs in Filesystem.objects.all():
                    volumes_list.extend(self.get_volumes_per_fs(fs.name))
            return volumes_list
        except:
            raise Exception('POST call API_Exception:get_volumes(filesystem_name) => Failed to get the list of Volumes for filesystem=%s' %filesystem_name)
    @classmethod
    def get_volumes_per_fs (self,filesystem_name):
        try:
            volume_list = []
            filesystem = Filesystem.objects.get(name = filesystem_name)
            volume_list.append(
                               {
                                'id' : filesystem.id,
                                'name': filesystem.name,
                                'targetpath': '', 
                                'kind': 'FS', #filesystem.role(),
                                'status' : filesystem.status_string()
                                }
                               )
        except:
            raise Exception('API sub call Exception:get_volumes_per_fs(filesystem_name) => Failed to get the File system Volume for filesystem=%s' %filesystem_name)
        
        try:
            volume_list.append(
                            {
                                'id' : filesystem.mgs.id,
                                'name': filesystem.mgs.name,
                                'targetpath' : '',
                                'kind': filesystem.mgs.role(),
                                'status' : filesystem.mgs.status_string()
                            }
            )
        except ManagementTarget.DoesNotExist:
            pass
        try:
            mdt = MetadataTarget.objects.get (filesystem = filesystem)
            volume_list.append(
                            {
                                'id' : mdt.id,
                                'name': mdt.name,
                                'targetpath': '',
                                'kind': mdt.role(),
                                'status' : mdt.status_string()
                            }
            )            
        except MetadataTarget.DoesNotExist:
             pass
        try:
            osts = ObjectStoreTarget.objects.filter(filesystem = filesystem)
            volume_list.extend([
                                {
                                 'id' : ost.id,
                                 'name': ost.name,
                                 'targetpath': '',
                                 'kind': ost.role(),
                                 'status' : ost.status_string()
                                }  
                                for ost in osts
                               ])
            return volume_list
        except:
            raise Exception('API sub call Exception:get_volumes_per_fs(filesystem_name) => Failed to get the OST volumes for filesystem=%s' %filesystem_name)  

class GetClients (AnonymousRequestHandler):
         
    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_clients)

    @classmethod
    @extract_request_args(filesystem_name='filesystem')
    def get_clients(self,request,filesystem_name):
        try:
            if filesystem_name :
                return self.__get_clients(filesystem_name)
            else:
                client_list = []
                for filesystem in Filesystem.objects.all():
                    client_list.extend(self.__get_clients(filesystem.name))
            return client_list
        except:
            raise Exception('POST call API_Exception:get_clients(filesystem_name) => Failed to get the list of Clients for filesystem=%s' %filesystem_name)                      
    @classmethod 
    def __get_clients(self,filesystem_name):
        try:
            fsname = Filesystem.objects.get(name = filesystem_name)
            return [
                    { 
                     'id' : client.id,
                     'host' : client.host.address,
                     'mount_point' : client.mount_point,
                      #'status' : self.__mountable_audit_status(client)
                    }         
                    for client in Client.objects.filter(filesystem = fsname)
            ]
        except:
            raise Exception('API sub call Exception:__get_clients(filesystem_name) => Failed to get the list of Clients for filesystem=%s' %filesystem_name)

class GetServers (AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.list_servers)

    @classmethod
    def list_servers(self,request):
        try:
            return [
                    { 
                     'id' : host.id,
                     'host_address' : host.address,
                     'failnode':'',
                     'kind' : host.role() ,
                     'lnet_status' : host.status_string()
                    }
                    for host in Host.objects.all()
            ]
        except:
            raise Exception('GET call API_Exception:list_servers() => Failed to get list of servers')

class AddHost(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.add_host)

    @classmethod
    @extract_request_args(host_name='hostname')
    def add_host(self,request,host_name):
        try:
            host, ssh_monitor =SshMonitor.from_string(host_name)
            host.save()
            ssh_monitor.host = host
            ssh_monitor.save
            return {
                    'host':host_name,
                    'status': 'added'
                   }
        except:
            raise Exception('POST call API_Exception:add_host(host_name) => Failed to add host %s' % host_name)   

#TODO:
#     This chart data API call is a place holder for r3d layer interface data fetch
#     Currently i am passing the cooked up data using random function till we get
#     actual data from the r3d layer
#     API interface and chart data format will ramain same
class GetFSDiskUsage(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_fs_diskusage)

    @classmethod
    @extract_request_args(filesystem_name='filesystem',start_time='starttime',end_time='endtime' ,data_function='datafunction')
    def get_fs_diskusage(self,request,filesystem_name,start_time,end_time ,data_function):
        from random import uniform
        try:
            if filesystem_name :
                return [ 
                        {
                         'timestamp' : '1316847600',
                         'filesystem' : filesystem_name,
                         'kbytesfree' : uniform(0,4940388537.9860001),
                         'kbytestotal': '4940834834.4740801',
                        }
                       ]
            else :
                return [
                        {
                         'timestamp' : '1316847600',
                         'filesystem' : filesystem.name,
                         'kbytesfree' : uniform(0,4940388537.9860001),
                         'kbytestotal': '4940834834.4740801',
                        }
                        for filesystem in Filesystem.objects.all() 
                ]      
        except:
            raise  Exception('POST call API_Exception:get_fs_diskusage(filesystem_name,start_time,end_time ,data_function) => Failed to get data for inputs filesystem=%s|starttime=%s|endtime%s |datafunction=%s' %filesystem_name %start_time %end_time   %data_function)

#TODO:
#     This chart data API call is a place holder for r3d layer interface data fetch
#     Currently i am passing the cooked up data using random function till we get
#     actual data from the r3d layer
#     API interface and chart data format will ramain same
class GetFSInodesUsage(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_fs_indoesusage)

    @classmethod
    @extract_request_args(filesystem_name='filesystem',start_time='starttime',end_time='endtime' ,data_function='datafunction')
    def get_fs_indoesusage(self,request,filesystem_name,start_time,end_time ,data_function):
        from random import randrange
        try:
            if filesystem_name :
                return [
                        {
                         'timestamp' : '1316847600',
                         'filesystem' : filesystem_name,
                         'filesfree' : randrange(0,4940388537,3),
                         'filestotal': '4940834834',
                        }
                       ]
            else :
                return [
                        {
                         'timestamp' : '1316847600',
                         'filesystem' : filesystem.name,
                         'filesfree' : randrange(0,4940388537,3),
                         'filestotal': '4940834834',
                        }
                        for filesystem in Filesystem.objects.all()
                ]
        except:
            raise  Exception('POST call API_Exception:get_fs_inodesusage(filesystem_name,start_time,end_time ,data_function) => Failed to get data for inputs filesystem=%s|starttime=%s|endtime%s |datafunction=%s' %filesystem_name %start_time %end_time   %data_function)

#TODO:
#     This chart data API call is a place holder for r3d layer interface data fetch
#     Currently i am passing the cooked up data using random function till we get
#     actual data from the r3d layer
#     API interface and chart data format will ramain same
class GetServerCPUUsage(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_server_cpuusage)

    @classmethod
    @extract_request_args(host_name='hostname',start_time='starttime',end_time='endtime' ,data_function='datafunction')
    def get_server_cpuusage(self,request,host_name,start_time,end_time ,data_function):
        try:
            from  random import randrange
            data_slice = [] 
            current_slice = gettimeslice()
            if host_name :
                for slice in current_slice:
                    data_slice.append(    
                                      {
                                       'timestamp': slice,
                                       'hostname' : host_name,
                                       'cpu' : randrange(0,100,3),
                                      }
                                     ) 
                return data_slice    
            else :
                for host in Host.objects.all():
                    for slice in current_slice:
                        data_slice.append(
                                          {
                                           'timestamp': slice,
                                           'hostname' : host.address,
                                           'cpu' : randrange(0,100,3),
                                          }
                                         )
                return data_slice                       
        except:
            raise Exception('POST call API_Exception:get_server_cpuusage(host_name,start_time,end_time ,data_function) => Failed to get data for inputs hostname=%s|starttime=%s|endtime%s |datafunction=%s' %host_name %start_time %end_time   %data_function)

#TODO:
#     This chart data API call is a place holder for r3d layer interface data fetch
#     Currently i am passing the cooked up data using random function till we get
#     actual data from the r3d layer
#     API interface and chart data format will ramain same
class GetServerMemoryUsage(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_server_memoryusage)

    @classmethod
    @extract_request_args(host_name='hostname',start_time='starttime',end_time='endtime' ,data_function='datafunction')
    def get_server_memoryusage(self,request,host_name,start_time,end_time ,data_function):
        try:
            from  random import randrange
            data_slice = []
            current_slice = gettimeslice()
            if host_name :
                for slice in current_slice:
                    data_slice.append(
                                      {
                                       'timestamp': slice,
                                       'hostname' : host_name,
                                       'memory' : randrange(1024,16384,3),
                                      }
                                     )
                return data_slice
            else :
                for host in Host.objects.all():
                    for slice in current_slice:
                        data_slice.append(
                                          {
                                           'timestamp': slice,
                                           'hostname' : host.address,
                                           'memory' : randrange(1024,16384,3),
                                          }
                                         )
                return data_slice
        except:
            raise  Exception('POST call API_Exception:get_server_memoryusage(host_name,start_time,end_time ,data_function) => Failed to get data for inputs hostname=%s|starttime=%s|endtime%s |datafunction=%s' %host_name %start_time %end_time   %data_function)

#TODO:
#     This chart data API call is a place holder for r3d layer interface data fetch
#     Currently i am passing the cooked up data using random function till we get
#     actual data from the r3d layer
#     API interface and chart data format will ramain same
class GetTargetReads(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_target_reads)

    @classmethod
    @extract_request_args(target_name='targetname',start_time='starttime',end_time='endtime' ,data_function='datafunction')
    def get_target_reads(self,request,target_name,start_time,end_time ,data_function):
        try:
            from random import randrange
            data_slice = []
            current_slice = gettimeslice()
            if target_name :
                for slice in current_slice:
                    data_slice.append(    
                                      {
                                       'timestamp' : slice,
                                       'targetname' : target_name,
                                       'reads' : randrange(1024,16384,3),
                                      }
                                     )
                return data_slice 
            else :
                 volume_list = []
                 for fs in Filesystem.objects.all():
                    try:
                        for slice in current_slice:
                            data_slice.append(
                                              {
                                               'timestamp' : slice,
                                               'targetname' : fs.mgs.name,
                                               'reads' : randrange(1024,16384,3),
                                              }
                                             )
                    except ManagementTarget.DoesNotExist:
                        pass
                    try:
                        mdt = MetadataTarget.objects.get(filesystem = fs)
                        volume_list.append(
                                           {
                                            'timestamp' : slice,
                                            'targetname' : mdt.name,
                                            'reads' : randrange(1024,16384,3),
                                           }
                                          )
                    except MetadataTarget.DoesNotExist:
                        pass
                    try:
                        osts = ObjectStoreTarget.objects.filter(filesystem = fs)
                        for ost in osts:
                            for slice in current_slice:  
                                data_slice.append(
                                                  {
                                                   'timestamp' :slice,
                                                   'targetname' : ost.name,
                                                   'reads' : randrange(1024,16384,3),
                                                  }
                                                 )
                    except:
                        pass 
                    return data_slice
        except:
            raise  Exception('POST call API_Exception:get_target_reads(target_name,start_time,end_time ,data_function) => Failed to get data for inputs targetname=%s|starttime=%s|endtime%s |datafunction=%s' %target_name %start_time %end_time   %data_function)

#TODO:
#     This chart data API call is a place holder for r3d layer interface data fetch
#     Currently i am passing the cooked up data using random function till we get
#     actual data from the r3d layer
#     API interface and chart data format will ramain same
class GetTargetWrites(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_target_writes)

    @classmethod
    @extract_request_args(target_name='targetname',start_time='starttime',end_time='endtime' ,data_function='datafunction')
    def get_target_writes(self,request,target_name,start_time,end_time ,data_function):
        try:
            from random import randrange
            data_slice = []
            current_slice = gettimeslice()
            if target_name :
                for slice in current_slice:
                    data_slice.append(
                                      {
                                       'timestamp' : slice,
                                       'targetname' : target_name,
                                       'writes' : randrange(1024,16384,3),
                                      }
                                     )
                return data_slice
            else :
                 volume_list = []
                 for fs in Filesystem.objects.all():
                    try:
                        for slice in current_slice:
                            data_slice.append(
                                              {
                                               'timestamp' : slice,
                                               'targetname' : fs.mgs.name,
                                               'writes' : randrange(1024,16384,3),
                                              }
                                             )
                    except ManagementTarget.DoesNotExist:
                        pass
                    try:
                        mdt = MetadataTarget.objects.get(filesystem = fs)
                        volume_list.append(
                                           {
                                            'timestamp' : slice,
                                            'targetname' : mdt.name,
                                            'writes' : randrange(1024,16384,3),
                                           }
                                          )
                    except MetadataTarget.DoesNotExist:
                        pass
                    try:
                        osts = ObjectStoreTarget.objects.filter(filesystem = fs)
                        for ost in osts:
                            for slice in current_slice:
                                data_slice.append(
                                                  {
                                                   'timestamp' : slice,
                                                   'targetname' : ost.name,
                                                   'writes' : randrange(1024,16384,3),
                                                  }
                                                 )
                    except:
                        pass
                    return data_slice
        except:
            raise Exception('POST call API_Exception:get_target_writes(target_name,start_time,end_time ,data_function) => Failed to get data for inputs targetname=%s|starttime=%s|endtime%s |datafunction=%s' %target_name %start_time %end_time   %data_function)


class GetEventsByFilter(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_events_by_filter)

    @classmethod
    @extract_request_args(host_name='hostname',severity_type='severity',event_type='eventtype',scroll_size='scrollsize',scroll_id='scrollid')
    def get_events_by_filter(self,request,host_name,severity_type,event_type,scroll_size,scroll_id):
        try:
            from monitor.models import Event
            filter_args = []
            filter_kwargs = {}
            if event_type :
                from django.db.models import Q
                event_type = event_type.lower
                filter_args.append(~Q(**{event_type:None}))
            event_set = Event.objects.filter(*filter_args, **filter_kwargs).order_by('-created_at')  
            return [
                    {
                     'event_created_at': event.created_at,
                     'event_host': event.host.pretty_name(),
                     'event_severity':str(event.severity_class()),
                     'event_message': event.message(), 
                    }
                    for event in event_set
            ]
        except:
            raise Exception('POST call API_Exception:get_events_by_filter(host_name,severity_type,event_type,scroll_size,scroll_id) => Failed to get filtered events for input hostname=%s|severity=%s|eventtype=%s|scrollsize=%s|scrollid=%s' %host_name %severity_type %event_type %scroll_size %scroll_id)

class GetLatestEvents(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_latest_events)

    @classmethod
    def get_latest_events(self,request):
        try:
            from monitor.models import Event
            return [
                    {
                     'event_created_at': event.created_at,
                     'event_host': event.host.pretty_name(),
                     'event_severity':str(event.severity_class()), # Still need to figure out wheather to pass enum or display string
                     'event_message': event.message(),
                    }
                    for event in Event.objects.all().order_by('-created_at')
            ]
        except:
            raise Exception('GET call API_Exception:get_latest_events() => Failed to get the latest events.')


class GetAlerts(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_alerts)

    @classmethod
    @extract_request_args(active_flag='active')
    def get_alerts(self,request,active_flag):
        try :
            from monitor.models import AlertState
            if active_flag ==  'True':
                return [
                        {
                         'alert_created_at': alert.begin,
                         'alert_created_at_short': alert.begin,
                         'alert_severity':'alert', # Still need to figure out wheather to pass enum or display string.
                         'alert_item': str(alert.alert_item), 
                         'alert_message': alert.message(),
                        }
                        for alert in  AlertState.objects.filter(active = True).order_by('end')
                ]
            else :
                return [
                        {
                         'alert_created_at': alert.begin,
                         'alert_created_at_short': alert.begin,
                         'alert_severity':'alert', # Still need to figure out wheather to pass enum or display string.
                         'alert_item': str(alert.alert_item),
                         'alert_message': alert.message(),
                        }
                        for alert in  AlertState.objects.filter(active = False).order_by('end')
                ]
        except :
            raise Exception('POST call API_Exception:get_alerts(active_flag) => Failed to get alert data where active_flag is %s' %active_flag)



class GetJobs(AnonymousRequestHandler):

    def __init__(self,*args,**kwargs):
        AnonymousRequestHandler.__init__(self,self.get_jobs)

    @classmethod
    def get_jobs(self,request):
        try:
            from configure.models import Job
            from datetime import timedelta, datetime
            from django.db.models import Q
            # Only retive Job logs for past 60 minutes.
            # This need to fixed to get jobs for any time delta
            # Need input from PM    
            jobs = Job.objects.filter(~Q(state = 'complete') | Q(created_at__gte=datetime.now() - timedelta(minutes=60)))
            return [
                        {
                         'id': job.id,
                         'state': job.state,
                         'errored': job.errored,
                         'cancelled': job.cancelled,
                         'created_at': "%s" % job.created_at,
                         'description': job.description(),
                        }
                        for job in jobs
            ]
        except:
            raise Exception('GET call API_Exception:get_jobs () => unable to retrive alerts')


def gettimeslice(sample_size=10,interval=5):
    from datetime import timedelta,datetime
    current_time = datetime.now()
    data_slice = []
    for i in xrange(sample_size):
        current_time  = current_time - timedelta(seconds=interval)
        strtime  = current_time.isoformat().split('T')[1]
        data_slice.append(strtime.split('.')[0])
    return data_slice

