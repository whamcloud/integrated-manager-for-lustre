#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================
# REST API Conrtoller for Lustre File systems resource monitor name space
from django.core.management import setup_environ

# Hydra server imports
import settings
setup_environ(settings)

from django.contrib.contenttypes.models import ContentType

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
        from configure.lib.state_manager import StateManager 
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

            # FIXME: fsid and fsname are bad names, they should be 'id' and 'name'
            filesystems.append({'fsid':filesystem.id,
                                'fsname': filesystem.name,
                                'status':filesystem.status_string(),
                                'available_transitions': StateManager.available_transitions(filesystem),
                                'noofoss':no_of_oss,
                                'noofost':no_of_ost,
                                'mgs_hostname': filesystem.mgs.primary_server().pretty_name(),
                                'mds_hostname': mds_hostname,
                                # FIXME: the API should not be formatting these, leave it to the presentation layer
                                'kbytesused': sizeof_fmt((fskbytestotal * 1024)),
                                'kbytesfree': sizeof_fmt((fskbytesfree *1024)),
                                'id': filesystem.id,
                                'content_type_id': ContentType.objects.get_for_model(filesystem).id
                                 })

        return filesystems

class GetFileSystem(AnonymousRequestHandler):
    @extract_request_args('filesystem_id')
    def run(self,request,filesystem_id):
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


        # FIXME: why return a list of one?
        fs_info = []  
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
                         'inodes_used':(fsfilestotal - fsfilesfree),
                         'id': filesystem.id,
                         'content_type_id': ContentType.objects.get_for_model(filesystem).id

        })
        return fs_info  

class GetMgtDetails(AnonymousRequestHandler):
    def run(self,request):
        from configure.lib.state_manager import StateManager
        all_mgt = []
        for mgt in ManagedMgs.objects.all():
            target_info = mgt.to_dict()
            target_info['fs_names'] = [fs.name for fs in ManagedFilesystem.objects.filter(mgs=mgt)]
            target_info['available_transitions'] = StateManager.available_transitions(mgt)
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
        host_filter = None
        if host_id:
            host_filter = ManagedHost.objects.get(id=host_id)
        
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
                if host_filter:
                    if ManagedTargetMount.objects.filter(target = t, host = host_filter).count() == 0:
                        continue

                result.append({
                    'id': t.id,
                    'primary_server_name': t.primary_server().pretty_name(),
                    'kind': kind,
                    'status':t.status_string(),
                    'label': t.human_name()
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
    @extract_request_args('host_id','severity','eventtype','page_id','page_size')
    def run(self,request,host_id,severity,eventtype,page_size,page_id):
        return geteventsbyfilter(host_id,severity,eventtype,page_id,page_size)

def geteventsbyfilter(host_id,severity,eventtype,page_id,page_size,sort_column=None):
    from monitor.models import Event
    host = None
    filter_args = []
    filter_kwargs = {}
    if severity:
        filter_kwargs['severity'] = severity
    if host_id:
        host = ManagedHost.objects.get(id=host_id)
        filter_kwargs['host'] = host
    if eventtype:
         klass = eventtype
         from django.db.models import Q
         klass_lower = klass.lower()
         filter_args.append(~Q(**{klass_lower: None}))
    
    events = Event.objects.filter(*filter_args, **filter_kwargs).order_by('-created_at')
    
    def format_fn(event):
        return {
                 'date': event.created_at.strftime("%b %d %H:%M:%S"),
                 'event_host': event.host.pretty_name() if event.host else '',
                 'event_severity':str(event.severity_class()),
                 'event_message': event.message() 
               }
    return paginate_result(page_id, page_size, events, format_fn)  

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
    @extract_request_args('active','page_id','page_size')
    def run(self,request,active,page_id,page_size):
        from monitor.models import AlertState
        if active:
            active = True
        else:
            active = None
        alerts = AlertState.objects.filter(active = active).order_by('end')

        def format_fn(alert):
            return alert.to_dict()

        return paginate_result(page_id, page_size, alerts, format_fn)

class GetJobs(AnonymousRequestHandler):
    def run(self,request):
        from configure.models import Job
        from datetime import timedelta, datetime
        from django.db.models import Q
        jobs = Job.objects.filter(~Q(state = 'complete') | Q(created_at__gte=datetime.now() - timedelta(minutes=60)))
        return [j.to_dict() for j in jobs]

class GetLogs(AnonymousRequestHandler):
    @extract_request_args('host_id','start_time','end_time','lustre','page_id','page_size')
    def run(self,request,host_id,start_time,end_time,lustre,page_id,page_size):
        return get_logs(host_id,start_time,end_time,lustre,page_id,page_size)

def get_logs(host_id,start_time,end_time,lustre,page_id,page_size,custom_search=None,sort_column=None):
    import datetime
    from monitor.models import Systemevents
    ui_time_format = "%m/%d/%Y %H:%M "
    host=None 
    filter_kwargs = {}
    if start_time:
        start_date = datetime.datetime.strptime(str(start_time),ui_time_format)
        filter_kwargs['devicereportedtime__gte'] = start_date
    if end_time:
        end_date = datetime.datetime.strptime(str(end_time),ui_time_format)
        filter_kwargs['devicereportedtime__lte'] = end_date
    if host_id:
        host = ManagedHost.objects.get(id=host_id)
        filter_kwargs['fromhost__startswith'] = host.pretty_name()
    if lustre == 'true':
        filter_kwargs['message__startswith'] = " Lustre"
    if custom_search:
        filter_kwargs['message__icontains'] = custom_search

    def log_class(log_entry):
        if log_entry.message.find('LustreError') != -1:
            return 'log_error'
        else:
            return 'log_info'
    
    def format_fn(systemevent_record):
        return {'message': nid_finder(systemevent_record.message),
                    # Trim trailing colon from e.g. 'kernel:'
                    'service': systemevent_record.syslogtag.rstrip(":"),
                    'date': systemevent_record.devicereportedtime.strftime("%b %d %H:%M:%S"),
                    'host': systemevent_record.fromhost,
                    'class': log_class(systemevent_record)
                   }

    log_data = Systemevents.objects.filter(**filter_kwargs).order_by('-devicereportedtime')
    return paginate_result(page_id, page_size, log_data, format_fn)

def paginate_result(page_id,page_size,result, format_fn):
    if page_id:
        offset = int(page_id)
    else:
        offset = 0
    # iTotalRecords is the number of records before filtering (where here filtering
    # means datatables filtering, not the filtering we're doing from our other args)
    iTotalRecords = result.count()
    # This is equal because we are not doing any datatables filtering here yet.
    iTotalDisplayRecords = iTotalRecords

    if page_size:
        result = result[offset:offset + page_size]

    # iTotalDisplayRecords is simply the number of records we will return
    # in this call (i.e. after all filtering and pagination)
    paginated_result = {}
    paginated_result['iTotalRecords'] = iTotalRecords
    paginated_result['iTotalDisplayRecords'] = iTotalDisplayRecords
    paginated_result['aaData'] = [format_fn(r) for r in result]
    return paginated_result

def nid_finder(message):
    from configure.models import Nid, ManagedTarget 
    from monitor.lib.lustre_audit import normalize_nid
    import re
    # TODO: detect IB/other(cray?) as well as tcp
    nid_regex = re.compile("(\d{1,3}\.){3}\d{1,3}@tcp(_\d+)?")
    target_regex = re.compile("\\b(\\w+-(MDT|OST)\\d\\d\\d\\d)\\b")
    for match in nid_regex.finditer(message):
        replace = match.group()
        replace = normalize_nid(replace)
        try:
            address = Nid.objects.get(nid_string = replace).lnet_configuration.host.address
            markup = "<a href='#' title='%s'>%s</a>" % (match.group(), address)
            message = message.replace(match.group(),
                                      markup)
        except Nid.DoesNotExist:
            print "failed to replace " + replace
    for match in target_regex.finditer(message):
        # TODO: look up to a target and link to something useful
        replace = match.group()
        #markup = "<a href='#' title='%s'>%s</a>" % ("foo", match.group())
        markup = match.group() 
        try:
            t = ManagedTarget.objects.get(name=markup) 
            markup =  "<a href='#' class='target target_id_%s'>%s</a>" %(t.id,t.human_name())
        except:
            pass
        message = message.replace(match.group(),
                                  markup,
                                  1)
    return message  
