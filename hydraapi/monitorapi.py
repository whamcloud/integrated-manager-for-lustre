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
from configure.models import (ManagedFilesystem,
                            ManagedMdt,
                            ManagedMgs,
                            ManagedOst,
                            ManagedHost,
                            ManagedTargetMount)
from monitor.lib.util import sizeof_fmt

class ListFileSystems(AnonymousRequestHandler):
    def run(self,request):
        filesystems = []
        mds_hostname = ''
        for filesystem in ManagedFilesystem.objects.all():
            osts = ManagedOst.objects.filter(filesystem = filesystem)
            no_of_ost = osts.count()
            no_of_oss = len(set([tm.host for tm in ManagedTargetMount.objects.filter(target__in = osts)]))
            no_of_oss = ManagedHost.objects.filter(managedtargetmount__target__in = osts).distinct().count()
            # if FS is created but MDT is no created we still want to display fs in list
            try:
               mds_hostname = ManagedMdt.objects.get(filesystem = filesystem).primary_server().pretty_name()     
            except:
                pass
            fskbytesfree  = 0
            fskbytestotal = 0
            #fsfilesfree  = 0
            #fsfilestotal = 0
            try:
                #inodedata = filesystem.metrics.fetch_last(ManagedMdt,fetch_metrics=["filesfree", "filestotal"])
                diskdata = filesystem.metrics.fetch_last(ManagedOst,fetch_metrics=["kbytesfree", "kbytestotal"])
                if diskdata:
                    fskbytesfree  = diskdata[1]['kbytesfree']
                    fskbytestotal = diskdata[1]['kbytestotal']  
                #if inodedata:
                #    fsfilesfree  = inodedata[1]['filesfree']
                #    fsfilestotal = inodedata[1]['filestotal']
            except:
                pass 

            filesystems.append({'fsid':filesystem.id,
                                'fsname': filesystem.name,
                                'status':filesystem.status_string(),
                                'noofoss':no_of_oss,
                                'noofost':no_of_ost,
                                'mgs_hostname': filesystem.mgs.primary_server().pretty_name(),
                                'mds_hostname': mds_hostname,
                                # FIXME: the API should not be formatting these, leave it to the presentation layer
                                'kbytesused': sizeof_fmt((fskbytestotal * 1024)),
                                'kbytesfree': sizeof_fmt((fskbytesfree *1024))})

        return filesystems

class GetFileSystem(AnonymousRequestHandler):
    @extract_request_args('filesystem_id')
    def run(self,request,filesystem_id):
        fs_info = []  
        filesystem =  ManagedFilesystem.objects.get(id=filesystem_id)
        osts = ManagedOst.objects.filter(filesystem = filesystem)
        no_of_ost = osts.count()
        no_of_oss = len(set([tm.host for tm in ManagedTargetMount.objects.filter(target__in = osts)]))
        no_of_oss = ManagedHost.objects.filter(managedtargetmount__target__in = osts).distinct().count()
        mds_hostname = ''
        mds_status ='' 
        # if FS is created but MDT is no created we still want to display fs in list
        try:
            mds_hostname = ManagedMdt.objects.get(filesystem = filesystem).primary_server().pretty_name()
            mds_status   = ManagedMdt.objects.get(filesystem = filesystem).primary_server().status_string()
        except:
            pass
        try:
            fskbytesfree = 0
            fskbytestotal = 0
            fsfilesfree = 0
            fsfilestotal = 0
            inodedata = filesystem.metrics.fetch_last(ManagedMdt,fetch_metrics=["filesfree", "filestotal"])
            diskdata = filesystem.metrics.fetch_last(ManagedOst,fetch_metrics=["kbytesfree", "kbytestotal"])
            if diskdata:
                fskbytesfree  = diskdata[1]['kbytesfree']
                fskbytestotal = diskdata[1]['kbytestotal']
            if inodedata:
                fsfilesfree  = inodedata[1]['filesfree']
                fsfilestotal = inodedata[1]['filestotal']
        except:
                pass

        fs_info.append( {'fsname':filesystem.name,
                         'status':filesystem.status_string(),
                         'noofoss':no_of_oss,
                         'noofost':no_of_ost,
                         'mgs_hostname':filesystem.mgs.primary_server().pretty_name(),
                         'mds_hostname':mds_hostname,
                         'mdsstatus':mds_status,
                         # FIXME: the API should not be formatting these, leave it to the presentation layer
                         'bytes_total':sizeof_fmt((fskbytestotal * 1024)),
                         'bytes_free':sizeof_fmt((fskbytesfree * 1024)),
                         'bytes_used':sizeof_fmt(((fskbytestotal - fskbytesfree) * 1024)),
                         'inodes_free':fsfilesfree,
                         'inodes_total':fsfilestotal,
                         'inodes_used':(fsfilestotal - fsfilesfree)
        })
        return fs_info  

class GetMgtDetails(AnonymousRequestHandler):
    def run(self,request):
        all_mgt = []
        for mgt in ManagedMgs.objects.all():
            target_info = mgt.to_dict()
            target_info['fs_names'] = [fs.name for fs in ManagedFilesystem.objects.filter(mgs=mgt)]
            all_mgt.append(target_info)
        return all_mgt

class GetFSVolumeDetails(AnonymousRequestHandler):
    @extract_request_args('filesystem_id')
    def run(self,request,filesystem_id):
        from configure.models import ManagedTarget, ManagedFilesystem
        if filesystem_id != None:
            filesystem = ManagedFilesystem.objects.get(pk = filesystem_id)
            targets = filesystem.get_targets()
        else:
            targets = ManagedTarget.objects.all()

        return [t.downcast().to_dict() for t in targets]

class GetTargets(AnonymousRequestHandler):
    @extract_request_args('filesystem', 'kinds')
    def run(self, request, filesystem, kinds):
        kind_map = {"MGT": ManagedMgs,
                    "OST": ManagedOst,
                    "MDT": ManagedMdt}

        if kinds:
            klasses = []
            for kind in kinds:
                try:
                    klasses.append(kind_map[kind])
                except KeyError:
                    raise RuntimeError("Unknown target kind '%s' (kinds are %s)" % (kind, kind_map.keys()))
        else:
            # kinds = None, means all
            klasses = kind_map.values()

        klass_to_kind = dict([(v,k) for k,v in kind_map.items()])
        result = []
        for klass in klasses:
            kind = klass_to_kind[klass]
            targets = klass.objects.all()
            for t in targets:
                result.append({
                    'id': t.id,
                    'primary_server_name': t.primary_server().pretty_name(),
                    'kind': kind,
                    # FIXME: ManagedTarget should get an explicit 'human' string function
                    # (currently __str__ services this purpose)
                    'label': "%s" % t
                    })
        return result

# FIXME: this is actually returning information about all filesystems, and all targets
# neither of which is a 'volume'.
class GetFSTargets(AnonymousRequestHandler):
    @extract_request_args('filesystem_id','kinds')
    def run(self, request, filesystem_id,kinds):
        kind_map = {"MGT": ManagedMgs,
                    "OST": ManagedOst,
                    "MDT": ManagedMdt}        
        if kinds:
            klasses = []
            for kind in kinds:
                try:
                    klasses.append(kind_map[kind])
                except KeyError:
                    raise RuntimeError("Unknown target kind '%s' (kinds are %s)" % (kind, kind_map.keys()))
        else:
            # kinds = None, means all
            klasses = kind_map.values()
        klass_to_kind = dict([(v,k) for k,v in kind_map.items()])
        result = []
        for klass in klasses:
            kind = klass_to_kind[klass]
            if klass == ManagedMgs:
                targets = klass.objects.all()
            else:
                if filesystem_id:
                    fs = ManagedFilesystem.objects.get(id=filesystem_id)
                    targets=klass.objects.filter(filesystem=fs) 
            for t in targets:
                result.append({
                    'id': t.id,
                    'primary_server_name': t.primary_server().pretty_name(),
                    'kind': kind,
                    # FIXME: ManagedTarget should get an explicit 'human' string function
                    # (currently __str__ services this purpose)
                    'status':t.status_string(),
                    'label': "%s" % t
                    })
        return result    

#class GetClients (AnonymousRequestHandler):
#    @extract_request_args('filesystem')
#    def run(self,request,filesystem):
#        filesystem_name = filesystem
#        if filesystem_name :
#            return self.__get_clients(filesystem_name)
#        else:
#            client_list = []
#            for filesystem in ManagedFilesystem.objects.all():
#                client_list.extend(self.__get_clients(filesystem.name))
##        return client_list
#    
#    def __get_clients(self,filesystem_name):
#        fsname = ManagedFilesystem.objects.get(name = filesystem_name)
#        return [
#                { 
#                 'id' : client.id,
#                 'host' : client.host.address,
#                 'mount_point' : client.mount_point,
#                  #'status' : self.__mountable_audit_status(client)
#                }         
#                for client in Client.objects.filter(filesystem = fsname)
#        ]

class GetServers (AnonymousRequestHandler):
    @extract_request_args('filesystem_id')
    def run(self,request,filesystem_id):
        if filesystem_id:
            fs = ManagedFilesystem.objects.get(id=filesystem_id)
            hosts = fs.get_servers()
        else:
            hosts = ManagedHost.objects.all()

        return [h.to_dict() for h in hosts]

class GetEventsByFilter(AnonymousRequestHandler):
    @extract_request_args('hostname','severity','eventtype','scrollsize','scrollid')
    def run(self,request,hostname,severity,eventtype,scrollsize,scrollid):
        #host_name=hostname
        #severity_type=severity
        event_type=eventtype
        #scroll_size=scrollsize
        #scroll_id=scrollid
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
                 'event_host': event.host.pretty_name() if event.host else '',
                 'event_severity':str(event.severity_class()),
                 'event_message': event.message(), 
                }
                for event in event_set
        ]

class GetLatestEvents(AnonymousRequestHandler):
    def run(self,request):
        from monitor.models import Event
        return [
                {
                 'event_created_at': event.created_at,
                 'event_host': event.host.pretty_name() if event.host else '',
                 'event_severity':str(event.severity_class()), # Still need to figure out wheather to pass enum or display string
                 'event_message': event.message(),
                }
                for event in Event.objects.all().order_by('-created_at')
        ]


class GetAlerts(AnonymousRequestHandler):
    @extract_request_args('active')
    def run(self,request,active):
        from monitor.models import AlertState
        return [a.to_dict() for a in AlertState.objects.filter(active = active).order_by('end')]

class GetJobs(AnonymousRequestHandler):
    def run(self,request):
        from configure.models import Job
        from datetime import timedelta, datetime
        from django.db.models import Q
        # Only retive Job logs for past 60 minutes.
        # This need to fixed to get jobs for any time delta
        # Need input from PM    
        jobs = Job.objects.filter(~Q(state = 'complete') | Q(created_at__gte=datetime.now() - timedelta(minutes=60)))

        return [j.to_dict() for j in jobs]

class GetLogs(AnonymousRequestHandler):
    @extract_request_args('month','day','lustre')
    def run(self,request,month,day,lustre):
        import datetime
        from monitor.models import Systemevents
        display_month = int(month)
        display_day = int(day) 
        if display_month == 0:
            start_date = datetime.datetime(1970, 1, 1)
        else:
            start_date = datetime.datetime(datetime.datetime.now().year,
                                           display_month, display_day)
        log_data = []
        log_data = Systemevents.objects.filter(devicereportedtime__gt =
                                               start_date).order_by('-devicereportedtime')
        if lustre:
            log_data = log_data.filter(message__startswith=" Lustre")
    
        return[
               { 
                'message': log_entry.message,
                'service': log_entry.syslogtag,
                'date': log_entry.devicereportedtime.strftime("%b %d %H:%M:%S"),
                'host': log_entry.fromhost,
               }
               for log_entry in log_data
        ]


def gettimeslice(sample_size=10,interval=5):
    from datetime import timedelta,datetime
    current_time = datetime.now()
    data_slice = []
    for i in xrange(sample_size):
        current_time  = current_time - timedelta(seconds=interval)
        strtime  = current_time.isoformat().split('T')[1]
        data_slice.append(strtime.split('.')[0])
    return data_slice

