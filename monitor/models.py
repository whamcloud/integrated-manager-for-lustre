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
        return [get_real_mountable(m) for m in self.mountable_set.all()]

    def role(self):
        roles = set()
        for t in self.mountable_set.all():
            t = get_real_mountable(t)
            if t.__class__ == ManagementTarget:
                roles.add("MGS")
            elif t.__class__ == MetadataTarget:
                roles.add("MDS")
            elif t.__class__ == ObjectStoreTarget:
                roles.add("OSS")
            elif t.__class__ == Client:
                roles.add("Client")

        if self.router_set.count() > 0:
            roles.add("Router")

        if len(roles) == 0:
            roles.add("Unused")

        return "/".join(roles)

    def status_string(self):
        # Green if all targets are online
        target_status_set = set([t.status_string() for t in self.mountable_set.all() if not hasattr(t, 'client')])
        if len(target_status_set) > 0:
            if target_status_set == set(["MOUNTED"]):
                return "OK"
            elif not "MOUNTED" in target_status_set:
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

class Router(models.Model):
    host = models.ForeignKey(Host)

class Filesystem(models.Model):
    name = models.CharField(max_length=8)

    def get_targets(self):
        return [self.get_mgs()] + self.get_filesystem_targets()

    def get_filesystem_targets(self):
        return list(MetadataTarget.objects.filter(filesystem = self).all()) + list(ObjectStoreTarget.objects.filter(filesystem = self).all())

    def get_mgs(self):
        return ManagementTarget.objects.get(filesystems = self)

    def get_servers(self):
        targets = self.get_targets()
        servers = defaultdict(list)
        for t in targets:
            servers[t.host].append(t)

        # NB converting to dict because django templates don't place nice with defaultdict
        # (http://stackoverflow.com/questions/4764110/django-template-cant-loop-defaultdict)
        return dict(servers)

    def status_string(self):
        # If all my targets are down, I'm red, even if my MGS is up
        if not "MOUNTED" in set([t.status_string() for t in self.get_filesystem_targets()]):
            return "OFFLINE"

        # If all my targets are up including the MGS, then I'm green
        if set([t.status_string() for t in self.get_targets()]) == set(["MOUNTED"]):
            return "OK"

        # Else I'm orange
        return "WARNING"

    def __str__(self):
        return "Filesystem '%s'" % self.name

class Mountable(models.Model):
    host = models.ForeignKey(Host)
    # Nullable because we might learn about a mountable on the MGS and
    # not know its mount point until we look at the server it's on.
    mount_point = models.CharField(max_length = 512, null = True, blank = True)

    def role(self):
        return get_real_mountable(self).role()

    def status_string(self):
        return AuditMountable.mountable_status_string(self)

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

    def __str__(self):
        if isinstance(self, LocalMountable):
            if self.name:
                name = self.name
            else:
                if isinstance(self, FilesystemMountable):
                    name = "%s-%sffff %s" % (self.filesystem.name, self.role(), self.id)
                else:
                    name = "%s %s" % (self.role(), self.id)
        else:
            if isinstance(self, FilesystemMountable):
                name = "%s-%s %s" % (self.filesystem.name, self.role(), self.id)
            else:
                name = "%s %s" % (self.role(), self.id)

        return name
        

class FilesystemMountable(models.Model):
    """A Mountable for a particular filesystem, such as 
       MDT, OST or Client"""
    filesystem = models.ForeignKey(Filesystem)

    def management_targets(self):
        mgts = ManagementTarget.objects.filter(filesystems__in = [self.filesystem])
        if len(mgts) == 0:
            raise ManagementTarget.DoesNotExist
        else:
            return mgts

class LocalMountable(Mountable):
    """NB the nullable-ness of the dev vs. name is a monitor vs. manage thing.  When
       you're managing, and you create volumes, you always have a dev but you may 
       not have a name til you format.  But when you're monitoring, you may learn
       a name from the MGS before you get to the host to learn the device.  This
       version of the class is monitoring-oriented"""
    # Like /dev/disk/by-path/ip-asdasdasd
    block_device = models.CharField(max_length = 512, null = True, blank = True)

    # Like testfs-OST0001
    name = models.CharField(max_length = 64)

    def name_no_fs(self):
        """Something like OST0001 rather than testfs1-OST0001"""
        if self.name:
            if self.name.find("-") != -1:
                return self.name.split("-")[1]
            else:
                return self.name
        else:
            return self.role()

class MetadataTarget(LocalMountable, FilesystemMountable):
    def role(self):
        return "MDT"

class ManagementTarget(LocalMountable):
    filesystems = models.ManyToManyField(Filesystem)
    def role(self):
        return "MGS"

class ObjectStoreTarget(LocalMountable, FilesystemMountable):
    def role(self):
        return "OST"

class Client(FilesystemMountable, Mountable):
    def role(self):
        return "Client"

def get_real_mountable(target):
    try:
        lm = target.localmountable
    except LocalMountable.DoesNotExist:
        return target.client

    try:
        return lm.metadatatarget
    except MetadataTarget.DoesNotExist:
        pass
    try:
        return lm.managementtarget
    except ManagementTarget.DoesNotExist:
        pass
    try:
        return lm.objectstoretarget
    except ObjectStoreTarget.DoesNotExist:
        pass

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

class AuditMountable(models.Model):
    """Everything we learned about a Mountable when auditing a Host"""
    # Reference audit and audithost in order to allow for the case
    # where we audit the volume on the 'wrong' host
    audit = models.ForeignKey(Audit)
    audit_host = models.ForeignKey(AuditHost)

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
                audit_mountable = audit_host.auditmountable_set.get(mountable = mountable)
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
admin.site.register(FilesystemMountable)
admin.site.register(LocalMountable)
admin.site.register(ManagementTarget)
admin.site.register(MetadataTarget)
admin.site.register(ObjectStoreTarget)
admin.site.register(Client)

admin.site.register(Audit)
admin.site.register(AuditHost)
admin.site.register(AuditNid)
admin.site.register(AuditMountable)
admin.site.register(AuditRecoverable)
