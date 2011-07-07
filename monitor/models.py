from django.db import models
from polymorphic.models import DowncastMetaclass

from collections_24 import defaultdict

import simplejson as json

from logging import INFO, WARNING

def status_style(status):
        return {
                "STARTED": "OK",
                "FAILOVER": "WARNING",
                "HA WARN": "WARNING",
                "RECOVERY": "WARNING",
                "REDUNDANT": "OK",
                "SPARE": "OK",
                "STOPPED": "OFFLINE",
                "???": "",
                "OFFLINE": "OFFLINE",
                "OK": "OK",
                "WARNING": "WARNING"
                }[status]

# Create your models here.
class Host(models.Model):
    address = models.CharField(max_length = 256, unique = True)

    def __str__(self):
        return self.pretty_name()

    def save(self, *args, **kwargs):
        from django.core.exceptions import ValidationError
        MIN_LENGTH = 1
        if len(self.address) < MIN_LENGTH:
            raise ValidationError("Address '%s' is too short" % self.address)
        super(Host, self).save(*args, **kwargs)

    def pretty_name(self):
        if self.address[-12:] == ".localdomain":
            return self.address[:-12]
        else:
            return self.address
    
    def role(self):
        roles = set()
        for mountable in self.mountable_set.all():
            if isinstance(mountable, TargetMount):
                target = mountable.target.downcast()
                if target.__class__ == ManagementTarget:
                    roles.add("MGS")
                elif target.__class__ == MetadataTarget:
                    roles.add("MDS")
                elif target.__class__ == ObjectStoreTarget:
                    roles.add("OSS")

            if isinstance(mountable, Client):
                roles.add("Client")

        if self.router_set.count() > 0:
            roles.add("Router")

        if len(roles) == 0:
            roles.add("Unused")

        return "/".join(roles)

    def status_string(self):
        # Green if all targets are online
        target_status_set = set([t.status_string() for t in self.mountable_set.all() if isinstance(t, TargetMount)])
        if len(target_status_set) > 0:
            good_states = ["STARTED", "REDUNDANT", "SPARE"]
            if set(good_states) >= target_status_set:
                return "OK"
            elif len(set(good_states) & target_status_set) == 0:
                return "OFFLINE"
            else:
                return "WARNING"
        else:
            # No local targets, just report lnet status
            lnet_status = AuditHost.lnet_status_string(self)
            if lnet_status == "UP":
                return "OK"
            else:
                return "OFFLINE"

class SshMonitor(models.Model):
    DEFAULT_AGENT_PATH = '/root/hydra-agent.py'
    DEFAULT_USERNAME = 'root'

    host = models.OneToOneField(Host)

    username = models.CharField(max_length = 64, blank = True, null = True)
    port = models.IntegerField(blank = True, null = True)
    agent_path = models.CharField(max_length = 512, blank = True, null = True)
    def get_agent_path(self):
        if self.agent_path:
            return self.agent_path
        else:
            return SshMonitor.DEFAULT_AGENT_PATH

    def get_username(self):
        if self.username:
            return self.username
        else:
            return SshMonitor.DEFAULT_USERNAME

    @staticmethod
    def from_string(address, agent_path = None):
        """Return an unsaved SshMonitor instance, with the Host either set to 
           an existing Host with the right address, or a new unsaved Host."""
        if address.find("@") != -1:
            user,host = address.split("@")
        else:
            user = None
            host = address

        if host.find(":") != -1:
            host, port = host.split(":")
        else:
            port = None

        agent_path = SshMonitor.DEFAULT_AGENT_PATH
        try:
            host = Host.objects.get(address = address)
        except Host.DoesNotExist:
            host = Host(address = address)

        return host, SshMonitor(
                host = host,
                username = user,
                port = port,
                agent_path = agent_path)

    def ssh_address_str(self):
        return "%s@%s" % (self.get_username(), self.host.address.__str__())

    def invoke(self):
        """Safe to call on an SshMonitor which has a host assigned, neither
        need to have been saved"""
        data = SshMonitor._invoke_many({self.host: self})
        result = data[self.host]
        if isinstance(result, Exception):
            raise result
        else:
            return result

    @staticmethod
    def invoke_many(hosts):
        """Only safe to call on hosts with SshMonitor children where
        both have been saved"""
        return SshMonitor._invoke_many(dict([[h, h.sshmonitor] for h in hosts]))

    @staticmethod
    def _invoke_many(host_ssh_map):

        # Build map of address to host for lookup after clustershell is 
        # invoked.
        host_map = dict([[v.ssh_address_str(), k] for k,v in host_ssh_map.items()])
        # TODO use sshmonitor.port if set (clustershell doesn't seem 
        # to support setting the port!?!)
        from ClusterShell.Task import task_self, NodeSet
        task = task_self()
        for host, ssh_monitor in host_ssh_map.items():
            task.shell(
                    ssh_monitor.get_agent_path(),
                    nodes = NodeSet.fromlist([ssh_monitor.ssh_address_str()]));
        task.resume()

        result = {}
        for output, nodes in task.iter_buffers():
            for node in nodes:
                host = host_map[node]
                try:
                    data = json.loads("%s" % output)
                except ValueError,e:
                    print "JSON parse failed: '%s'" % output
                    data = e
                
                result[host] = data

        return result


class Nid(models.Model):
    """Simplified NID representation for monitoring only"""
    host = models.ForeignKey(Host)
    nid_string = models.CharField(max_length=128)

class Router(models.Model):
    host = models.ForeignKey(Host)

class Filesystem(models.Model):
    name = models.CharField(max_length=8)
    mgs = models.ForeignKey('ManagementTarget')

    class Meta:
        unique_together = ('name', 'mgs')

    def get_targets(self):
        return [self.mgs] + self.get_filesystem_targets()

    def get_filesystem_targets(self):
        return list(MetadataTarget.objects.filter(filesystem = self).all()) + list(ObjectStoreTarget.objects.filter(filesystem = self).all())

    def get_servers(self):
        targets = self.get_targets()
        servers = defaultdict(list)
        for t in targets:
            for tm in t.targetmount_set.all():
                servers[tm.host].append(tm)

        # NB converting to dict because django templates don't place nice with defaultdict
        # (http://stackoverflow.com/questions/4764110/django-template-cant-loop-defaultdict)
        return dict(servers)

    def status_string(self):
        fs_statuses = set([t.status_string() for t in self.get_filesystem_targets()])

        good_status = set(["STARTED", "REDUNDANT", "SPARE"])
        # If all my targets are down, I'm red, even if my MGS is up
        if not good_status & fs_statuses:
            return "OFFLINE"

        all_statuses = fs_statuses | set([self.mgs.status_string()])

        # If all my targets are up including the MGS, then I'm green
        if all_statuses <= good_status:
            return "OK"

        # Else I'm orange
        return "WARNING"

    def status_rag(self):
        return status_style(self.status_string())

    def __str__(self):
        return self.name

class Mountable(models.Model):
    """Something that can be mounted on a particular host (roughly
       speaking a line in fstab."""
    __metaclass__ = DowncastMetaclass
    host = models.ForeignKey('Host')
    mount_point = models.CharField(max_length = 512, null = True, blank = True)

    def device(self):
        """To be implemented by child classes"""
        raise NotImplementedError()

    def role(self):
        """To be implemented by child classes"""
        raise NotImplementedError()

    def status_string(self):
        """To be implemented by child classes"""
        raise NotImplementedError()

    def status_rag(self):
        return status_style(self.status_string())

class FilesystemMember(models.Model):
    """A Mountable for a particular filesystem, such as 
       MDT, OST or Client"""
    filesystem = models.ForeignKey(Filesystem)

    # Use of abstract base classes to avoid django bug #12002
    class Meta:
        abstract = True

class TargetMount(Mountable):
    """A mountable (host+mount point+device()) which associates a Target
       with a particular location to mount as primary or as failover"""
    # Like /dev/disk/by-path/ip-asdasdasd
    block_device = models.CharField(max_length = 512, null = True, blank = True)
    primary = models.BooleanField()

    def save(self, force_insert = False, force_update = False, using = None):
        # If primary is true, then target must be unique
        if self.primary:
            from django.db.models import Q
            other_primaries = TargetMount.objects.filter(~Q(id = self.id), target = self.target).count()
            if other_primaries > 0:
                from django.core.exceptions import ValidationError
                raise ValidationError("Cannot have multiple primary mounts for target %s" % self.target)

        # If this is an MGS, there may not be another MGS on 
        # this host
        try:
            from django.db.models import Q
            mgs = self.target.managementtarget
            other_mgs_mountables_local = TargetMount.objects.filter(~Q(target__managementtarget = None), ~Q(id = self.id), host = self.host).count()
            if other_mgs_mountables_local > 0:
                from django.core.exceptions import ValidationError
                raise ValidationError("Cannot have multiple MGS mounts on host %s" % self.host.address)

        except ManagementTarget.DoesNotExist:
            pass

        return super(TargetMount, self).save(force_insert, force_update, using)

    target = models.ForeignKey('Target')

    def __str__(self):
        return "%s" % (self.target)

    def device(self):
        return self.block_device

    def status_string(self):
        this_status = AuditMountable.mountable_status_string(self)
        other_status = []
        for target_mount in self.target.targetmount_set.all():
            if target_mount != self:
                other_status.append(AuditMountable.mountable_status_string(target_mount))

        if len(other_status) == 0:
            return this_status
        else:
            if self.primary and this_status != "STARTED":
                if "STARTED" in other_status:
                    return "FAILOVER"
                else:
                    return "STOPPED"

            if self.primary and this_status == "STARTED":
                if "???" in other_status:
                    return "HA WARN"
                else:
                    return "REDUNDANT"

            if not self.primary:
                if this_status == "STARTED":
                    return "FAILOVER"
                elif this_status == "???":
                    return "???"
                else:
                    return "SPARE"

        raise NotImplementedError

    def status_rag(self):
        return status_style(self.status_string())

    def pretty_block_device(self):
        # Truncate to iSCSI iqn if possible
        parts = self.block_device.split("-iscsi-")
        if len(parts) == 2:
            return parts[1]
        
        # Strip /dev/mapper if possible
        parts = self.block_device.split("/dev/mapper/")
        if len(parts) == 2:
            return parts[1]

        # Strip /dev if possible
        parts = self.block_device.split("/dev/")
        if len(parts) == 2:
            return parts[1]

        # Fall through, do nothing
        return self.block_device

class Target(models.Model):
    """A Lustre filesystem target (MGS, MDT, OST) in the abstract, which
       may be accessible through 1 or more hosts via TargetMount"""
    __metaclass__ = DowncastMetaclass
    # Like testfs-OST0001
    # Nullable because when manager creates a Target it doesn't know the name
    # until it's formatted+started+audited
    name = models.CharField(max_length = 64, null = True, blank = True)

    def name_no_fs(self):
        """Something like OST0001 rather than testfs1-OST0001"""
        if self.name:
            if self.name.find("-") != -1:
                return self.name.split("-")[1]
            else:
                return self.name
        else:
            return self.downcast().role()

    def status_string(self):
        mount_statuses = set([target_mount.status_string() for target_mount in self.targetmount_set.all()])
        if "REDUNDANT" in mount_statuses:
            return "REDUNDANT"
        elif "FAILOVER" in mount_statuses:
            return "FAILOVER"
        elif "STARTED" in mount_statuses:
            return "STARTED"
        else:
            return "STOPPED"

    def status_rag(self):
        return status_style(self.status_string())

    def params(self):
        return AuditTarget.target_params(self)

    def __str__(self):
        if self.name:
            return self.name
        else:
            return "%s %s" % (self.__class__.__name__, self.id)

class MetadataTarget(Target, FilesystemMember):
    def role(self):
        return "MDT"

class ManagementTarget(Target):
    def role(self):
        return "MGS"

    @staticmethod
    def get_by_host(host):
        return ManagementTarget.objects.get(targetmount__host = host)

class ObjectStoreTarget(Target, FilesystemMember):
    def role(self):
        return "OST"

class Client(Mountable, FilesystemMember):
    def role(self):
        return "Client"

    def status_string(self):
        return AuditMountable.mountable_status_string(self)

    def __str__(self):
        return "%s-client %d" % (self.filesystem.name, self.id)


class Event(models.Model):
    __metaclass__ = DowncastMetaclass

    created_at = models.DateTimeField(auto_now = True)
    severity = models.IntegerField()
    host = models.ForeignKey(Host, blank = True, null = True)

    @staticmethod
    def type_name():
        raise NotImplementedError

    def severity_class(self):
        # CSS class from an Event severity -- FIXME: this should be a templatetag
        from logging import INFO, WARNING, ERROR
        return {INFO: 'info', WARNING: 'warning', ERROR: 'error'}[self.severity]

    def message(self):
        raise NotImplementedError

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import GenericForeignKey
class LearnEvent(Event):
    # Every environment at some point reinvents void* :-)
    learned_item_type = models.ForeignKey(ContentType)
    learned_item_id = models.PositiveIntegerField()
    learned_item = GenericForeignKey('learned_item_type', 'learned_item_id')

    @staticmethod
    def type_name():
        return "Autodetection"

    def message(self):
        if isinstance(self.learned_item, TargetMount):
            return "Discovered mount point of %s on %s" % (self.learned_item, self.learned_item.host)
        elif isinstance(self.learned_item, Target):
            return "Discovered formatted target %s" % (self.learned_item)
        elif isinstance(self.learned_item, Filesystem):
            return "Discovered filesystem %s on MGS %s" % (self.learned_item, self.learned_item.mgs.targetmount_set.get(primary = True).host)
        else:
            return "Discovered %s" % self.learned_item

class AlertEvent(Event):
    message_str = models.CharField(max_length = 512)
    alert = models.ForeignKey('AlertState')

    @staticmethod
    def type_name():
        return "Alert"

    def message(self):
        return self.message_str

class AlertState(models.Model):
    """Records a period of time during which a particular
       issue affected a particular element of the system"""
    __metaclass__ = DowncastMetaclass

    alert_item_type = models.ForeignKey(ContentType, related_name='alertstate_alert_item_type')
    alert_item_id = models.PositiveIntegerField()
    alert_item = GenericForeignKey('alert_item_type', 'alert_item_id')

    begin = models.DateTimeField()
    end = models.DateTimeField()
    active = models.BooleanField()

    def duration(self):
        return self.end - self.begin

    @classmethod
    def notify(alert_klass, alert_item, active):
        if active:
            alert_klass.high(alert_item)
        else:
            alert_klass.low(alert_item)

    @classmethod
    def get_existing(alert_klass, alert_item):
        """Do a normal .get() with the alert_item converted to explicit id+type info
           for GenericForeignKey"""
        return alert_klass.objects.get(
                active = True,
                alert_item_id = alert_item.id,
                alert_item_type__model = alert_item.__class__.__name__.lower(),
                alert_item_type__app_label = alert_item.__class__._meta.app_label)

    @classmethod
    def high(alert_klass, alert_item):
        import datetime
        now = datetime.datetime.now()
        try:
            alert_state = alert_klass.get_existing(alert_item)
            alert_state.end = now
            alert_state.save()
        except alert_klass.DoesNotExist:
            alert_state = alert_klass(
                    active = True,
                    begin = now,
                    end = now,
                    alert_item = alert_item)
            alert_state.save()
            alert_state.begin_event().save()

        return alert_state

    @classmethod
    def low(alert_klass, alert_item):
        import datetime
        now = datetime.datetime.now()
        try:
            alert_state = alert_klass.get_existing(alert_item)
            alert_state.end = now
            alert_state.active = False
            alert_state.save()
            alert_state.end_event().save()
        except alert_klass.DoesNotExist:
            alert_state = None

        return alert_state

class MountableOfflineAlert(AlertState):
    def message(self):
        if isinstance(self.alert_item, TargetMount):
            return "Target offline"
        elif isinstance(self.alert_item, Client):
            return "Client offline"
        else:
            raise NotImplementedError

    def begin_event(self):
        return AlertEvent(
                message_str = "%s stopped" % self.alert_item,
                host = self.alert_item.host,
                alert = self,
                severity = WARNING)
        
    def end_event(self):
        return AlertEvent(
                message_str = "%s started" % self.alert_item,
                host = self.alert_item.host,
                alert = self,
                severity = INFO)

class HostContactAlert(AlertState):
    def message(self):
        return "Host contact lost"

    def begin_event(self):
        return AlertEvent(
                message_str = "Lost contact with host %s" % self.alert_item,
                host = self.alert_item,
                alert = self,
                severity = WARNING)

    def end_event(self):
        return AlertEvent(
                message_str = "Re-established contact with host %s" % self.alert_item,
                host = self.alert_item,
                alert = self,
                severity = INFO)

class TargetRecoveryAlert(AlertState):
    def message(self):
        return "Target in recovery"

    def begin_event(self):
        return AlertEvent(
                message_str = "Target '%s' went into recovery" % self.alert_item,
                host = self.alert_item.host,
                alert = self,
                severity = WARNING)

    def end_event(self):
        return AlertEvent(
                message_str = "Target '%s' completed recovery" % self.alert_item,
                host = self.alert_item.host,
                alert = self,
                severity = INFO)

class LNetOfflineAlert(AlertState):
    def message(self):
        return "LNet offline"

    def begin_event(self):
        return AlertEvent(
                message_str = "LNet stopped on host '%s'" % self.alert_item,
                host = self.alert_item,
                alert = self,
                severity = WARNING)

    def end_event(self):
        return AlertEvent(
                message_str = "LNet started on host '%s'" % self.alert_item,
                host = self.alert_item,
                alert = self,
                severity = INFO)

class Audit(models.Model):
    """Represent an attempt to audit some hosts"""
    created_at = models.DateTimeField(auto_now = True)
    complete = models.BooleanField()
    attempted_hosts = models.ManyToManyField(Host)

class AuditHost(models.Model):
    """Represent a particular host which was successfully 
       contacted during an audit"""
    host = models.ForeignKey(Host)
    audit = models.ForeignKey(Audit)
    lnet_up = models.BooleanField()

    @staticmethod
    def lnet_status_string(host):
        # Latest audit that tried to contact our host
        try:
            audit = Audit.objects.filter(attempted_hosts = host, complete = True).latest('id')
        except Audit.DoesNotExist:
            return "???"

        try:
            audit_host = audit.audithost_set.get(host = host)
            return {True: "UP", False: "DOWN"}[audit_host.lnet_up]
        except AuditHost.DoesNotExist:
            # Last audit attempt on this host failed
            return "???"

class AuditNid(models.Model):
    audit_host = models.ForeignKey(AuditHost)
    nid_string = models.CharField(max_length=128)

class AuditTarget(models.Model):
    audit = models.ForeignKey(Audit)
    target = models.ForeignKey(Target)

    @staticmethod
    def target_params(target):
        """Unlike what we do for TargetMount status, when there isn't an up to date
           AuditTarget, we will return the last known parameters rather than '???'"""
        result = []
        try:
            audit_target = AuditTarget.objects.filter(target = target).latest('audit__created_at') 
            for param in audit_target.auditparam_set.all():
                result.append((param.key, param.value))
        except AuditTarget.DoesNotExist:
            pass

        return result

class AuditParam(models.Model):
    audit_target = models.ForeignKey(AuditTarget)
    key = models.CharField(max_length=128)
    value = models.CharField(max_length=512)

class AuditMountable(models.Model):
    """Everything we learned about a Mountable when auditing a Host"""
    # Reference audit and audithost in order to allow for the case
    # where we audit the volume on the 'wrong' host
    audit = models.ForeignKey(Audit)

    mountable = models.ForeignKey(Mountable)
    mounted = models.BooleanField()

    def __str__(self):
        return "Audit %s %s %s" % (self.audit.created_at, self.mountable.host, self.mountable)

    @staticmethod
    def mountable_status_string(mountable):
        # Latest audit that tried to contact our host
        try:
            audit = Audit.objects.filter(attempted_hosts = mountable.host, complete = True).latest('id')
        except Audit.DoesNotExist:
            return "???"

        try:
            audit_host = audit.audithost_set.get(host = mountable.host)
            try:
                audit_mountable = audit.auditmountable_set.get(mountable = mountable)
                try:
                    if audit_mountable.auditrecoverable.is_recovering():
                        return "RECOVERY"
                except AuditRecoverable.DoesNotExist:
                    pass

                return {True: "STARTED", False: "STOPPED"}[audit_mountable.mounted]
            except AuditMountable.DoesNotExist:
                # Does not appear in our scan: could just be unmounted on 
                # an fstabless host
                return "STOPPED"

        except AuditHost.DoesNotExist:
            # Last audit attempt on this host failed
            return "???"

class AuditRecoverable(AuditMountable):
    # When a volume is present, we will have been able to interrogate 
    # its recovery status
    # JSON-encoded dict parsed from /proc/fs/lustre/*/*/recovery_status
    recovery_status = models.CharField(max_length=512)

    def is_recovering(self):
        data = json.loads(self.recovery_status)
        return (data.has_key("status") and data["status"] == "RECOVERING")

    def recovery_status_str(self):
        data = json.loads(self.recovery_status)
        if data.has_key("status") and data["status"] == "RECOVERING":
            return "%s %ss remaining" % (data["status"], data["time_remaining"])
        elif data.has_key("status"):
            return data["status"]
        else:
            return "N/A"

from django.contrib import admin
admin.site.register(AuditHost)
admin.site.register(Audit)
admin.site.register(AuditMountable)
admin.site.register(AuditNid)
admin.site.register(AuditParam)
admin.site.register(AuditRecoverable)
admin.site.register(AuditTarget)
admin.site.register(Client)
admin.site.register(Filesystem)
admin.site.register(Host)
admin.site.register(ManagementTarget)
admin.site.register(MetadataTarget)
admin.site.register(Mountable)
admin.site.register(Nid)
admin.site.register(ObjectStoreTarget)
admin.site.register(Router)
admin.site.register(Target)
admin.site.register(TargetMount)

admin.site.register(Event)
admin.site.register(LearnEvent)
admin.site.register(AlertEvent)

