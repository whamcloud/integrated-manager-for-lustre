from django.db import models

from collections_24 import defaultdict

import simplejson as json

# Create your models here.
class Host(models.Model):
    address = models.CharField(max_length = 256)

    def __str__(self):
        return "Host '%s'" % self.address

    def get_mountables(self):
        """Like mountable_set.all() but downcasting to their most 
           specific class rather than returning a bunch of Mountable"""
        return [m.downcast() for m in self.mountable_set.all()]

    def role(self):
        roles = set()
        for mountable in self.mountable_set.all():
            mountable = mountable.downcast()
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
        target_status_set = set([t.status_string() for t in self.get_mountables() if not hasattr(t, 'client')])
        if len(target_status_set) > 0:
            good_states = ["MOUNTED", "REDUNDANT", "SPARE"]
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

class Nid(models.Model):
    """Simplified NID representation for monitoring only"""
    host = models.ForeignKey(Host)
    nid_string = models.CharField(max_length=128)

class Router(models.Model):
    host = models.ForeignKey(Host)

class Filesystem(models.Model):
    name = models.CharField(max_length=8)
    mgs = models.ForeignKey('ManagementTarget')
    # TODO: uniqueness constraint on name + MGS

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

        good_status = set(["MOUNTED", "REDUNDANT", "SPARE"])
        # If all my targets are down, I'm red, even if my MGS is up
        if not good_status & fs_statuses:
            return "OFFLINE"

        all_statuses = fs_statuses | set([self.mgs.status_string()])

        # If all my targets are up including the MGS, then I'm green
        if all_statuses <= good_status:
            return "OK"

        # Else I'm orange
        return "WARNING"

    def __str__(self):
        return "Filesystem '%s'" % self.name

class Mountable(models.Model):
    """Something that can be mounted on a particular host (roughly
       speaking a line in fstab."""
    host = models.ForeignKey('Host')
    mount_point = models.CharField(max_length = 512, null = True, blank = True)

    def device(self):
        """To be implemented by child classes"""
        raise NotImplementedError()

    def role(self):
        return self.downcast().role()

    def downcast(self):
        if self.__class__ != Mountable and isinstance(self, Mountable):
            return self
            
        try:
            return self.targetmount
        except TargetMount.DoesNotExist:
            pass

        try:
            return self.client
        except Client.DoesNotExist:
            pass

        print self, self.id

        raise NotImplementedError

    def status_string(self):
        raise NotImplementedError

    def status_rag(self):
        return {
                "MOUNTED": "OK",
                "FAILOVER": "WARNING",
                "HA WARN": "WARNING",
                "RECOVERY": "WARNING",
                "REDUNDANT": "OK",
                "SPARE": "OK",
                "UNMOUNTED": "OFFLINE",
                "???": ""
                }[self.status_string()]

class FilesystemMember(models.Model):
    """A Mountable for a particular filesystem, such as 
       MDT, OST or Client"""
    filesystem = models.ForeignKey(Filesystem)

    # Use of abstract base classes to avoid django bug #12002
    class Meta:
        abstract = True

    def management_targets(self):
        mgts = ManagementTarget.objects.filter(filesystems__in = [self.filesystem])
        if len(mgts) == 0:
            raise ManagementTarget.DoesNotExist
        else:
            return mgts

class TargetMount(Mountable):
    """A mountable (host+mount point+device()) which associates a Target
       with a particular location to mount as primary or as failover"""
    # Like /dev/disk/by-path/ip-asdasdasd
    block_device = models.CharField(max_length = 512, null = True, blank = True)
    # TODO: constraint that there can only be one primary for a target
    primary = models.BooleanField()

    # TODO: in the case of an MGS, constrain that there may not be two TargetMounts for the same host which 
    # both reference an MGS in 'target'

    target = models.ForeignKey('Target')

    def __str__(self):
        return "%s on %s" % (self.target, self.host.address)

    def status_string(self):
        this_status = AuditMountable.mountable_status_string(self)
        other_status = []
        for target_mount in self.target.targetmount_set.all():
            if target_mount != self:
                other_status.append(AuditMountable.mountable_status_string(target_mount))

        if len(other_status) == 0:
            return this_status
        else:
            if self.primary and this_status != "MOUNTED":
                if "MOUNTED" in other_status:
                    return "FAILOVER"
                else:
                    return "UNMOUNTED"

            if self.primary and this_status == "MOUNTED":
                if "???" in other_status:
                    return "HA WARN"
                else:
                    return "REDUNDANT"

            if not self.primary:
                if this_status == "MOUNTED":
                    return "FAILOVER"
                elif this_status == "???":
                    return "???"
                else:
                    return "SPARE"

        raise NotImplementedError

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
    # Like testfs-OST0001
    # Nullable because when manager creates a Target it doesn't know the name
    # until it's formatted+started+audited
    name = models.CharField(max_length = 64, null = True, blank = True)

    def downcast(self):
        try:
            return self.metadatatarget
        except MetadataTarget.DoesNotExist:
            pass
        try:
            return self.objectstoretarget
        except ObjectStoreTarget.DoesNotExist:
            pass
        try:
            return self.managementtarget
        except ManagementTarget.DoesNotExist:
            pass

        raise NotImplementedError

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
        elif "MOUNTED" in mount_statuses:
            return "MOUNTED"
        else:
            return "UNMOUNTED"

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

                return {True: "MOUNTED", False: "UNMOUNTED"}[audit_mountable.mounted]
            except AuditMountable.DoesNotExist:
                # Does not appear in our scan: could just be unmounted on 
                # an fstabless host
                return "UNMOUNTED"

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
admin.site.register(Host)
admin.site.register(Filesystem)
admin.site.register(Mountable)
admin.site.register(ManagementTarget)
admin.site.register(MetadataTarget)
admin.site.register(ObjectStoreTarget)
admin.site.register(Client)
admin.site.register(Audit)
admin.site.register(AuditHost)
admin.site.register(AuditNid)
admin.site.register(AuditMountable)
admin.site.register(AuditRecoverable)
