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
        from configure.lib.state_manager import StateManager
        if filesystem_id != None:
            filesystem = ManagedFilesystem.objects.get(pk = filesystem_id)
            targets = filesystem.get_targets()
        else:
            targets = ManagedTarget.objects.all()
        targets_info = []
        for t in targets:
            _target = t.to_dict()
            _target['available_transitions']  = StateManager.available_transitions(t)
            targets_info.append(_target)  
        return targets_info

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
    @extract_request_args('filesystem_id','host_id','kinds')
    def run(self, request, filesystem_id,host_id,kinds):
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
        host_name=None
        if host_id:
            host_name = (ManagedHost.objects.get(id=host_id)).address  
        
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
                if ( not host_name or t.primary_server().pretty_name() == host_name):   
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
        from configure.lib.state_manager import StateManager
        if filesystem_id:
            fs = ManagedFilesystem.objects.get(id=filesystem_id)
            hosts = fs.get_servers()
        else:
            hosts = ManagedHost.objects.all()
        hosts_info = []
        for h in hosts:
            _host = h.to_dict()
            _host['available_transitions'] = StateManager.available_transitions(h)
            hosts_info.append(_host)
        return hosts_info

class GetEventsByFilter(AnonymousRequestHandler):
    @extract_request_args('host_id','severity','eventtype','scroll_size','scroll_id')
    def run(self,request,host_id,severity,eventtype,scroll_size,scroll_id):
        from monitor.models import Event
        if scroll_id:
            offset = int(scroll_id)
        else:
            offset = 0
        if scroll_size:
            limit = int(scroll_size)
        else:
            limit = 0
        filter_args = []
        filter_kwargs = {}
        if severity:
            filter_kwargs['severity'] = severity
        if eventtype:
             klass = eventtype
             from django.db.models import Q
             klass_lower = klass.lower()
             filter_args.append(~Q(**{klass_lower: None}))
        if host_id:
            try:
                host = ManagedHost.objects.get(id=host_id)
            except:
                host = None
        event_set = Event.objects.filter(*filter_args, **filter_kwargs).order_by('-created_at')
        if host:
            event_set = event_set.filter(host=host)

        iTotalRecords = event_set.count()
        event_result = {}
        event_result['sEcho']=offset
        event_result['iTotalRecords'] = iTotalRecords
        event_result['iTotalDisplayRecords'] = offset * limit
        if limit == 0:
            limit = iTotalRecords
        rec_end_limit = (offset+1)*limit
        event_result['aaData'] = [
                                  {
                                   'event_created_at': event.created_at,
                                   'event_host': event.host.pretty_name() if event.host else '',
                                   'event_severity':str(event.severity_class()),
                                   'event_message': event.message(), 
                                   }
                                   for event in event_set[offset*limit: rec_end_limit if rec_end_limit < iTotalRecords else iTotalRecords]
                                  ]
        return event_result  

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
    @extract_request_args('active','scroll_id','scroll_size')
    def run(self,request,active,scroll_id,scroll_size):
        from monitor.models import AlertState
        if scroll_id:
            offset = int(scroll_id)
        else:
            offset = 0
        if scroll_size:
            limit = int(scroll_size)
        else:
            limit = 0
        if active:
            active = 'True'
        alerts = AlertState.objects.filter(active = active).order_by('end')
        iTotalRecords = alerts.count()
        alert_result = {}
        alert_result['sEcho']=offset
        alert_result['iTotalRecords'] = iTotalRecords
        alert_result['iTotalDisplayRecords'] = offset * limit
        if limit == 0:
            limit = iTotalRecords
        rec_end_limit = (offset+1)*limit
        alert_result['aaData'] = [a.to_dict() for a in alerts[offset*limit: rec_end_limit if rec_end_limit < iTotalRecords else iTotalRecords]]
        return alert_result

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
    @extract_request_args('start_time','end_time','lustre','scroll_id','scroll_size')
    def run(self,request,start_time,end_time,lustre,scroll_id,scroll_size):
        # FIXME: scroll_id is a misleading name, should be scroll_offset or page_id
        import datetime
        from monitor.models import Systemevents
        ui_time_format = "%m/%d/%Y %H:%M "
        host=None 

        if scroll_id:
            offset = int(scroll_id) * scroll_size
        else:
            offset = 0

        filter_kwargs = {}
        if start_time:
            start_date = datetime.datetime.strptime(str(start_time),ui_time_format)
            filter_kwargs['devicereportedtime__gte'] = start_date
        if end_time:
            end_date = datetime.datetime.strptime(str(end_time),ui_time_format)
            filter_kwargs['devicereportedtime__lte'] = end_date
        if host:
            filter_kwargs['fromhost_startswith'] = host
        if lustre:
            filter_kwargs['message__startswith'] = " Lustre"


        log_data = Systemevents.objects.filter(**filter_kwargs).order_by('-devicereportedtime')
        # iTotalRecords is the number of records before filtering (where here filtering
        # means datatables filtering, not the filtering we're doing from our other args)
        iTotalRecords = log_data.count()

        if scroll_size:
            log_data = log_data.all()[offset:offset + scroll_size]

        # iTotalDisplayRecords is simply the number of records we will return
        # in this call (i.e. after all filtering and pagination)
        iTotalDisplayRecords = log_data.count()
        log_records = [
                       { 
                        'message': nid_finder(log_entry.message),
                        'service': log_entry.syslogtag,
                        'date': log_entry.devicereportedtime.strftime("%b %d %H:%M:%S"),
                        'host': log_entry.fromhost,
                       }
                       for log_entry in log_data
        ]
        log_result = {}
        log_result['sEcho']=offset
        log_result['iTotalRecords'] = iTotalRecords
        log_result['iTotalDisplayRecords'] = iTotalDisplayRecords
        log_result['aaData'] = log_records
        return log_result              

def normalize_nid(string):
    """Cope with the Lustre and users sometimes calling tcp0 'tcp' to allow
       direct comparisons between NIDs"""
    if string[-4:] == "@tcp":
        string += "0"
     # remove _ from nids (i.e. @tcp_0 -> @tcp0
    i = string.find("_")
    if i > -1:
        string = string[:i] + string [i + 1:]
    return string

def nid_finder(message):
    from configure.models import Nid
    import re
    nid_regex = re.compile("(\d{1,3}\.){3}\d{1,3}@tcp(_\d+)?")
    target_regex = re.compile("\\b(\\w+-(MDT|OST)\\d\\d\\d\\d)\\b")
    for match in nid_regex.finditer(message):
        replace = match.group()
        replace = normalize_nid(replace)
        try:
            address =  Nid.objects.get(nid_string = replace).lnet_configuration.host.address
            markup = "<a href='#' title='%s'>%s</a>" % (match.group(), address)
            message = message.replace(match.group(),
                                      markup,
                                      1)
        except Nid.DoesNotExist:
            print "failed to replace " + replace
    for match in target_regex.finditer(message):
        # TODO: look up to a target and link to something useful
        replace = match.group()
        markup = "<a href='#' title='%s'>%s</a>" % ("foo", match.group())
        message = message.replace(match.group(),
                                  markup,
                                  1)
    return message  
