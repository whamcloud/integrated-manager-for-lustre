#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import datetime
from exceptions import Exception
import json
import logging
import dateutil.parser

from django.db import models
from django.db import transaction
from django.db import IntegrityError
import itertools
from django.db.models.aggregates import Max, Count
from django.db.models.query_utils import Q
from django.utils.timezone import now
from chroma_core.lib.cache import ObjectCache
from chroma_core.models import StateChangeJob
from chroma_core.models.agent_session import AgentSession
from chroma_core.models.alert import AlertState
from chroma_core.models.event import AlertEvent

from chroma_core.models.jobs import StatefulObject, Job, AdvertisedJob, StateLock
from chroma_core.lib.job import job_log
from chroma_core.lib.job import  DependOn, DependAll, Step

from chroma_core.models.utils import MeasuredEntity, DeletableDowncastableMetaclass, DeletableMetaclass, Version

import settings


# FIXME: HYD-1367: Chroma 1.0 Job objects aren't amenable to using m2m
# attributes for this because:
# * constructor in command_run_jobs doesn't know how to deal with them
# * assigning them requires model to be saved first, which means
#   we can't e.g. check deps before saving job
class HostListMixin(models.Model):
    class Meta:
        abstract = True
        app_label = 'chroma_core'

    host_ids = models.CharField(max_length = 512)

    @property
    def hosts(self):
        if not self.host_ids:
            return ManagedHost.objects
        else:
            return ManagedHost.objects.filter(id__in = json.loads(self.host_ids))


class DeletableStatefulObject(StatefulObject):
    """Use this class to create your own downcastable classes if you need to override 'save', because
    using the metaclass directly will override your own save method"""
    __metaclass__ = DeletableDowncastableMetaclass

    class Meta:
        abstract = True
        app_label = 'chroma_core'


class ManagedHost(DeletableStatefulObject, MeasuredEntity):
    # FIXME: either need to make address non-unique, or need to
    # associate objects with a child object, because there
    # can be multiple servers on one hostname, eg ddn10ke
    address = models.CharField(max_length = 255, help_text = "A URI like 'user@myhost.net:22'")

    # A fully qualified domain name like flint02.testnet
    fqdn = models.CharField(max_length = 255, blank = True, null = True, help_text = "Unicode string, fully qualified domain name")

    # a nodename to match against fqdn in corosync output
    nodename = models.CharField(max_length = 255, blank = True, null = True, help_text = "Unicode string, node name")

    # A basic authentication mechanism
    agent_token = models.CharField(max_length = 64)

    # FIXME: HYD-1215: separate the LNET state [unloaded, down, up] from the host state [created, removed]
    states = ['unconfigured', 'configured', 'lnet_unloaded', 'lnet_down', 'lnet_up', 'removed']
    initial_state = 'unconfigured'

    last_contact = models.DateTimeField(blank = True, null = True, help_text = "When the Chroma agent on this host last sent an update to this server")

    DEFAULT_USERNAME = 'root'

    class Meta:
        app_label = 'chroma_core'
        unique_together = ('address',)

    def __str__(self):
        return self.pretty_name()

    def get_label(self):
        return self.pretty_name()

    def save(self, *args, **kwargs):
        from django.core.exceptions import ValidationError
        MIN_LENGTH = 1
        if len(self.address) < MIN_LENGTH:
            raise ValidationError("Address '%s' is too short" % self.address)

        if self.fqdn:
            try:
                ManagedHost.objects.get(~Q(pk = self.pk), fqdn = self.fqdn)
                raise IntegrityError("FQDN %s in use" % self.fqdn)
            except ManagedHost.DoesNotExist:
                pass

        super(ManagedHost, self).save(*args, **kwargs)

    def is_available(self):
        """Whether the Host is in contact"""
        if not self.last_contact:
            # Never had contact
            return False
        else:
            # Have we had contact within timeout?
            time_since = now() - self.last_contact
            return time_since <= datetime.timedelta(seconds=settings.AUDIT_PERIOD * 2)

    def get_available_states(self, begin_state):
        if self.immutable_state:
            if begin_state == 'unconfigured':
                return ['removed', 'configured']
            else:
                return ['removed']
        else:
            return super(ManagedHost, self).get_available_states(begin_state)

    @classmethod
    def create_from_string(cls, address_string):
        # Single transaction for creating Host and related database objects
        # * Firstly because we don't want any of these unless they're all setup
        # * Secondly because we want them committed before creating any Jobs which
        #   will try to use them.
        with transaction.commit_on_success():
            try:
                host = ManagedHost.objects.get(address = address_string)
                # It already existed
                raise IntegrityError("Duplicate address %s" % address_string)
            except ManagedHost.DoesNotExist:
                import uuid
                # NB: this is NOT A CRYPTOGRAPHICALLY SECURE RANDOM NUMBER,
                # it is a very lightweight security measure intended primarily
                # to make the system more robust
                token = uuid.uuid4().__str__()
                host = ManagedHost.objects.create(address = address_string, agent_token = token)

            lnet_configuration, created = LNetConfiguration.objects.get_or_create(host = host)

        # Attempt some initial setup jobs
        from chroma_core.models.jobs import Command
        command = Command.set_state([(host, 'configured')], "Setting up host %s" % address_string)

        return host, command

    def pretty_name(self):
        # Take FQDN if we have it, or fall back to address
        if self.fqdn:
            name = self.fqdn
        else:
            user, host, port = self.ssh_params()
            name = host

        if name[-12:] == ".localdomain":
            return name[:-12]
        else:
            return name

    def _role_strings(self):
        roles = set()
        for mountable in self.managedtargetmount_set.all():
            target = mountable.target.downcast()
            roles.add("%sS" % target.role()[:-1])

            #if isinstance(mountable, Client):
            #    roles.add("Client")

        #if self.router_set.count() > 0:
        #    roles.add("Router")

        return roles

    def is_unused(self):
        return (len(self._role_strings()) == 0)

    def is_mgs(self):
        from chroma_core.models.target import ManagedMgs
        try:
            ManagedMgs.objects.get(managedtargetmount__host = self)
            return True
        except ManagedMgs.DoesNotExist:
            return False

    def available_lun_nodes(self):
        from chroma_core.models import ManagedTargetMount
        used_luns = [i['block_device__lun'] for i in ManagedTargetMount.objects.all().values('volume_node__volume')]
        return VolumeNode.objects.filter(
                ~Q(lun__in = used_luns),
                host = self)

    def role(self):
        roles = self._role_strings()
        if len(roles) == 0:
            return "Unused"
        else:
            return "/".join(roles)

    def ssh_params(self):
        if self.address.find("@") != -1:
            user, host = self.address.split("@")
        else:
            user = self.DEFAULT_USERNAME
            host = self.address

        if host.find(":") != -1:
            host, port = host.split(":")
        else:
            port = None

        return user, host, port

    @classmethod
    def get_by_nid(cls, nid_string):
        """Resolve a NID string to a ManagedHost (best effort).  Not guaranteed to work:
         * The NID might not exist for any host
         * The NID might exist for multiple hosts

         Note: this function may return deleted hosts (useful behaviour if you're e.g. resolving
         NID to hostname for historical logs).
        """

        hosts = ManagedHost._base_manager.filter(lnetconfiguration__nid__nid_string = nid_string)
        # We can resolve the NID to a host if there is exactly one not-deleted
        # host with that NID (and 0 or more deleted hosts), or if there are
        # no not-deleted hosts with that NID but exactly one deleted host with that NID
        if hosts.count() == 0:
            raise ManagedHost.DoesNotExist()
        elif hosts.count() == 1:
            return hosts[0]
        else:
            active_hosts = [h for h in hosts if h.not_deleted]
            if len(active_hosts) > 1:
                # If more than one not-deleted host has this NID, we cannot pick one
                raise ManagedHost.MultipleObjectsReturned()
            else:
                fqdns = set([h.fqdn for h in hosts])
                if len(fqdns) == 1:
                    # If all the hosts with this NID had the same FQDN, pick one to return
                    if len(active_hosts) > 0:
                        # If any of the hosts were not deleted, prioritize that
                        return active_hosts[0]
                    else:
                        # Else return an arbitrary one
                        return hosts[0]
                else:
                    # If the hosts with this NID had different FQDNs, refuse to pick one
                    raise ManagedHost.MultipleObjectsReturned()

    def set_state(self, state, intentional = False):
        """
        :param intentional: set to true to silence any alerts generated by this transition
        """
        from chroma_core.models import LNetOfflineAlert

        super(ManagedHost, self).set_state(state, intentional)
        if intentional:
            LNetOfflineAlert.notify_quiet(self, self.state != 'lnet_up')
        else:
            LNetOfflineAlert.notify(self, self.state != 'lnet_up')


class Volume(models.Model):
    storage_resource = models.ForeignKey(
        'StorageResourceRecord', blank = True, null = True, on_delete = models.PROTECT)

    # Size may be null for VolumeNodes created when setting up
    # from a JSON file which just tells us a path.
    size = models.BigIntegerField(blank = True, null = True,
            help_text = "Integer number of bytes.  Can be null if this device \
                    was manually created, rather than detected.")

    label = models.CharField(max_length = 128)

    __metaclass__ = DeletableMetaclass

    class Meta:
        unique_together = ('storage_resource',)
        app_label = 'chroma_core'

    @classmethod
    def get_unused_luns(cls, queryset = None):
        """Get all Luns which are not used by Targets"""
        if not queryset:
            queryset = cls.objects.all()

        queryset = queryset.annotate(any_targets = Max('volumenode__managedtargetmount__target__not_deleted'))
        return queryset.filter(any_targets = None)

    @classmethod
    def get_usable_luns(cls, queryset = None):
        """Get all Luns which are not used by Targets and have enough VolumeNode configuration
        to be used as a Target (i.e. have only one node or at least have a primary node set)"""
        if not queryset:
            queryset = cls.objects.all()

        # Luns are usable if they have only one VolumeNode (i.e. no HA available but
        # we can definitively say where it should be mounted) or if they have
        # a primary VolumeNode (i.e. one or more VolumeNodes is available and we
        # know at least where the primary mount should be)
        return queryset.filter(volumenode__host__not_deleted = True).\
                annotate(
                    any_targets = Max('volumenode__managedtargetmount__target__not_deleted'),
                    has_primary = Max('volumenode__primary'),
                    num_volumenodes = Count('volumenode')
                ).filter((Q(num_volumenodes = 1) | Q(has_primary = 1.0)) & Q(any_targets = None))

    def get_kind(self):
        """:return: A string or unicode string which is a human readable noun corresponding
        to the class of storage e.g. LVM LV, Linux partition, iSCSI LUN"""
        if not self.storage_resource_id:
            return "Unknown"

        from chroma_core.models import StorageResourceRecord
        record = StorageResourceRecord.objects.get(pk = self.storage_resource_id)
        resource_klass = record.to_resource_class()
        return resource_klass._meta.label

    def _get_label(self):
        if not self.storage_resource_id:
            if self.label:
                return self.label
            else:
                if self.volumenode_set.count():
                    volumenode = self.volumenode_set.all()[0]
                    return "%s:%s" % (volumenode.host, volumenode.path)
                else:
                    return ""

        # TODO: this is a link to the local e.g. ScsiDevice resource: to get the
        # best possible name, we should follow back to VirtualDisk ancestors, and
        # if there is only one VirtualDisk in the ancestry then use its name
        from chroma_core.models import StorageResourceRecord
        record = StorageResourceRecord.objects.get(pk = self.storage_resource_id)
        resource = record.to_resource()
        if record.alias:
            return record.alias
        else:
            return resource.get_label()

    def save(self, *args, **kwargs):
        self.label = self._get_label()
        super(Volume, self,).save(*args, **kwargs)

    def ha_status(self):
        """Tell the caller two things:
         * is the Volume configured enough for use as a target?
         * is the configuration (if present) HA?
         by returning one of 'unconfigured', 'configured-ha', 'configured-noha'
        """
        volumenode_count = self.volumenode_set.count()
        primary_count = self.volumenode_set.filter(primary = True).count()
        failover_count = self.volumenode_set.filter(primary = False, use = True).count()
        if volumenode_count == 1 and primary_count == 0:
            return 'configured-noha'
        elif volumenode_count == 1 and primary_count > 0:
            return 'configured-noha'
        elif primary_count > 0 and failover_count == 0:
            return 'configured-noha'
        elif primary_count > 0 and failover_count > 0:
            return 'configured-ha'
        else:
            # Has no VolumeNodes, or has >1 but no primary
            return 'unconfigured'


class VolumeNode(models.Model):
    volume = models.ForeignKey(Volume)
    host = models.ForeignKey(ManagedHost)
    path = models.CharField(max_length = 512, help_text = "Device node path, e.g. '/dev/sda/'")

    __metaclass__ = DeletableMetaclass

    storage_resource = models.ForeignKey('StorageResourceRecord', blank = True, null = True)

    primary = models.BooleanField(default = False, help_text = "Whether this node should\
            be used for the primary Lustre server when creating a target")

    use = models.BooleanField(default = True, help_text = "Whether this node should \
            be used as a Lustre server when creating a target (if primary is not set,\
            this node will be used as a secondary server")

    class Meta:
        unique_together = ('host', 'path')
        app_label = 'chroma_core'

    def __str__(self):
        return "%s:%s" % (self.host, self.path)

    def pretty_string(self):
        from chroma_core.lib.util import sizeof_fmt
        volume_label = self.volume.get_label()
        if volume_label:
            short_name = volume_label
        elif self.path.startswith('/dev/disk/by-path/'):
            short_name = self.path.replace('/dev/disk/by-path/', '', 1)

            # e.g. ip-192.168.122.1:3260-iscsi-iqn.2011-08.com.whamcloud.lab.hydra-1.sdb-lun-0
            if short_name.startswith("ip-") and short_name.find("-iscsi-") != -1:
                iscsi_iqn = "".join(short_name.split("-iscsi-")[1:])
                short_name = "iSCSI %s" % iscsi_iqn

            # e.g. /dev/disk/by-path/pci-0000:00:06.0-scsi-0:0:3:0
            if short_name.startswith("pci-") and short_name.find("-scsi-") != -1:
                scsi_id = "".join(short_name.split("-scsi-")[1:])
                short_name = "SCSI %s" % scsi_id

            # e.g. /dev/disk/by-path/pci-0000:0a:00.0-fc-0x21000001ff040a42:0x0006000000000000
            if short_name.startswith("pci-") and short_name.find("-fc-") != -1:
                fc_id = "".join(short_name.split("-fc-")[1:])
                short_name = "FC %s" % fc_id

        elif self.path.startswith('/dev/mapper/'):
            # e.g. /dev/mapper/VolGroup00-blob0
            short_name = self.path.replace('/dev/mapper/', '', 1)
            short_name = "DM %s" % short_name
        elif self.path.startswith('/dev/'):
            # e.g. /dev/sda
            short_name = self.path.replace('/dev/', '', 1)
        else:
            short_name = self.path

        size = self.volume.size
        if size:
            human_size = sizeof_fmt(size)
        else:
            human_size = "[size unknown]"

        return "%s (%s)" % (short_name, human_size)


class LNetConfiguration(StatefulObject):
    states = ['nids_unknown', 'nids_known']
    initial_state = 'nids_unknown'

    host = models.OneToOneField('ManagedHost')

    def get_nids(self):
        if self.state != 'nids_known':
            raise NoLNetInfo("Nids not known yet for host %s" % self.host)
        return [n.nid_string for n in self.nid_set.all()]

    def __str__(self):
        return "%s LNet configuration" % (self.host)

    class Meta:
        app_label = 'chroma_core'


class Nid(models.Model):
    """Simplified NID representation for those we detect already-configured"""
    lnet_configuration = models.ForeignKey(LNetConfiguration)
    nid_string = models.CharField(max_length=128)

    class Meta:
        app_label = 'chroma_core'


class LearnNidsStep(Step):
    idempotent = True

    def run(self, kwargs):
        from chroma_core.models import ManagedHost, Nid
        from chroma_core.lib.lustre_audit import normalize_nid
        host = ManagedHost.objects.get(pk = kwargs['host_id'])
        result = self.invoke_agent(host, "lnet-scan")

        self.log("Scanning NIDs on host %s..." % host)

        nids = []
        for nid_string in result:
            nid, created = Nid.objects.get_or_create(
                    lnet_configuration = host.lnetconfiguration,
                    nid_string = normalize_nid(nid_string))
            if created:
                self.log("Learned new nid %s:%s" % (host, nid.nid_string))
            nids.append(nid)

        for old_nid in Nid.objects.filter(~Q(id__in = [n.id for n in nids]), lnet_configuration = host.lnetconfiguration):
            self.log("Removed old nid %s:%s" % (host, old_nid.nid_string))
            old_nid.delete()


class ConfigureLNetJob(StateChangeJob):
    state_transition = (LNetConfiguration, 'nids_unknown', 'nids_known')
    stateful_object = 'lnet_configuration'
    lnet_configuration = models.ForeignKey(LNetConfiguration)
    state_verb = 'Configure LNet'

    def description(self):
        return "Configure LNet on %s" % self.lnet_configuration.host

    def get_steps(self):
        return [(LearnNidsStep, {'host_id': self.lnet_configuration.host_id})]

    def get_deps(self):
        return DependOn(ObjectCache.get_one(ManagedHost, lambda mh: mh.id == self.lnet_configuration.host_id), "lnet_up")

    class Meta:
        app_label = 'chroma_core'


class ConfigureRsyslogStep(Step):
    idempotent = True

    def run(self, kwargs):
        if settings.LOG_SERVER_HOSTNAME:
            fqdn = settings.LOG_SERVER_HOSTNAME
        else:
            import socket
            fqdn = socket.getfqdn()

        from chroma_core.models import ManagedHost
        host = ManagedHost.objects.get(id = kwargs['host_id'])
        if not host.immutable_state:
            self.invoke_agent(host, "configure-rsyslog --node %s" % fqdn)


class ConfigureNTPStep(Step):
    idempotent = True

    def run(self, kwargs):
        if settings.NTP_SERVER_HOSTNAME:
            fqdn = settings.NTP_SERVER_HOSTNAME
        else:
            import socket
            fqdn = socket.getfqdn()

        from chroma_core.models import ManagedHost
        host = ManagedHost.objects.get(id = kwargs['host_id'])
        if not host.immutable_state:
            self.invoke_agent(host, "configure-ntp --node %s" % fqdn)


class UnconfigureRsyslogStep(Step):
    idempotent = True

    def run(self, kwargs):
        from chroma_core.models import ManagedHost
        host = ManagedHost.objects.get(id = kwargs['host_id'])
        if not host.immutable_state:
            self.invoke_agent(host, "unconfigure-rsyslog")


class UnconfigureNTPStep(Step):
    idempotent = True

    def run(self, kwargs):
        from chroma_core.models import ManagedHost
        host = ManagedHost.objects.get(id = kwargs['host_id'])
        if not host.immutable_state:
            self.invoke_agent(host, "unconfigure-ntp")


class GetLNetStateStep(Step):
    idempotent = True

    def run(self, kwargs):
        from chroma_core.models import ManagedHost
        host = ManagedHost.objects.get(id = kwargs['host_id'])

        lustre_data = self.invoke_agent(host, "device-plugin --plugin=lustre")['lustre']

        if lustre_data['lnet_up']:
            state = 'lnet_up'
        elif lustre_data['lnet_loaded']:
            state = 'lnet_down'
        else:
            state = 'lnet_unloaded'

        host.set_state(state)
        host.save()


class GetLNetStateJob(Job):
    host = models.ForeignKey(ManagedHost)
    requires_confirmation = False
    verb = "Get LNet state"

    class Meta:
        app_label = 'chroma_core'

    def create_locks(self):
        return [StateLock(
            job = self,
            locked_item = self.host,
            begin_state = "configured",
            end_state = None,
            write = True
        )]

    @classmethod
    def get_args(cls, host):
        return {'host_id': host.id}

    def description(self):
        return "Get LNet state for %s" % self.host

    def get_steps(self):
        return [(GetLNetStateStep, {'host_id': self.host.id})]


class GetHostProperties(Step):
    idempotent = True

    def run(self, kwargs):
        from chroma_core.models import ManagedHost
        host = ManagedHost.objects.get(id = kwargs['host_id'])
        host_properties = self.invoke_agent(host, "host-properties")
        manager, agent = Version(settings.VERSION), Version(host_properties.get('agent_version'))
        # only check production version compatibility: A.B.
        if manager and agent and not (manager.major == agent.major and manager.minor >= agent.minor):
            raise ValueError("Version incompatibility between manager {0} and agent {1}".format(manager, agent))

        # Get agent capabilities
        capabilities = host_properties['capabilities']
        immutable_state = not any("manage_" in c for c in capabilities)
        if host.immutable_state != immutable_state:
            host.immutable_state = immutable_state
            host.save()

        # Get FQDN and nodename
        fqdn = host_properties['fqdn']
        nodename = host_properties['nodename']

        assert fqdn != None
        assert nodename != None

        from django.db import IntegrityError
        try:
            host.fqdn = fqdn
            host.nodename = nodename
            host.save()
            job_log.info("Learned FQDN '%s' for host %s (%s)" % (fqdn, host.pk, host.address))
        except IntegrityError:
            # TODO: make this an Event or Alert?
            host.fqdn = None
            job_log.error("Cannot complete setup of host %s, it is reporting an already-used FQDN %s" % (host, fqdn))
            raise

        if host_properties['selinux_enabled']:
            job_log.error("Cannot complete setup of host %s, SELinux is not disabled" % host)
            raise RuntimeError("SELinux must be disabled on %s" % host)


class GetHostClock(Step):
    idempotent = True

    def run(self, kwargs):

        from chroma_core.models import ManagedHost
        host = ManagedHost.objects.get(id = kwargs['host_id'])
        host_properties = self.invoke_agent(host, "host-properties")

        # Get agent time and check it against server time
        agent_time_str = host_properties['time']
        agent_time = dateutil.parser.parse(agent_time_str)
        server_time = now()
        from dateutil import tz
        server_time = server_time.replace(tzinfo=tz.tzutc())

        if agent_time > server_time:
            if (agent_time - server_time) > datetime.timedelta(seconds = settings.AGENT_CLOCK_TOLERANCE):
                raise RuntimeError("Host %s clock is fast.  agent time %s, server time %s" % (host, agent_time, server_time))

        if server_time > agent_time:
            if (server_time - agent_time) > datetime.timedelta(seconds = settings.AGENT_CLOCK_TOLERANCE):
                raise RuntimeError("Host %s clock is slow.  agent time %s, server time %s" % (host, agent_time, server_time))


class SetServerConfStep(Step):
    idempotent = True

    def run(self, kwargs):
        import settings

        from chroma_core.models import ManagedHost
        host = ManagedHost.objects.get(id = kwargs['host_id'])
        if settings.SERVER_HTTP_URL:
            url = settings.SERVER_HTTP_URL
        else:
            import socket
            fqdn = socket.getfqdn()
            url = "http://%s/" % fqdn
        self.invoke_agent(host, "set-server-conf", {"url": url, 'token': host.agent_token})


class RemoveServerConfStep(Step):
    idempotent = True

    def run(self, kwargs):
        from chroma_core.models import ManagedHost
        host = ManagedHost.objects.get(id = kwargs['host_id'])
        self.invoke_agent(host, "remove-server-conf")


class LearnDevicesStep(Step):
    idempotent = True

    def run(self, kwargs):
        from chroma_core.services.plugin_runner.agent_daemon_interface import AgentDaemonQueue, AgentDaemonRpcInterface
        # Get the device-scan output
        host = ManagedHost.objects.get(id = kwargs['host_id'])
        updates = self.invoke_agent(host, "device-plugin")
        try:
            del updates['lustre']
        except KeyError:
            pass

        # Fake a session as if the agent had reported in
        with transaction.commit_on_success():
            session, created = AgentSession.objects.get_or_create(host = host)

        AgentDaemonQueue().put({
                    "session_id": session.session_id,
                    "counter": 1,
                    "started_at": now().isoformat() + "Z",
                    "host_id": host.id,
                    "updates": updates
            })

        AgentDaemonRpcInterface().await_session(kwargs['host_id'])


class SetupHostJob(StateChangeJob):
    state_transition = (ManagedHost, 'unconfigured', 'configured')
    stateful_object = 'managed_host'
    managed_host = models.ForeignKey(ManagedHost)
    state_verb = 'Set up server'

    def description(self):
        return "Set up server %s" % self.managed_host

    def get_steps(self):
        return [(GetHostProperties, {'host_id': self.managed_host.pk}),
                (ConfigureNTPStep, {'host_id': self.managed_host.pk}),
                (GetHostClock, {'host_id': self.managed_host.pk}),
                (ConfigureRsyslogStep, {'host_id': self.managed_host.pk}),
                (LearnDevicesStep, {'host_id': self.managed_host.pk}),
                (SetServerConfStep, {'host_id': self.managed_host.pk})]

    class Meta:
        app_label = 'chroma_core'


class EnableLNetJob(StateChangeJob):
    state_transition = (ManagedHost, 'configured', 'lnet_unloaded')
    stateful_object = 'managed_host'
    managed_host = models.ForeignKey(ManagedHost)
    # Hide this transition as it does not actually do
    # anything (should go away with HYD-1215)
    state_verb = None

    def description(self):
        return "Enable LNet on %s" % self.managed_host

    def get_steps(self):
        return []

    class Meta:
        app_label = 'chroma_core'


class DetectTargetsStep(Step):
    def is_dempotent(self):
        return True

    def run(self, kwargs):
        from chroma_core.models import ManagedHost
        from chroma_core.lib.detection import DetectScan

        # Get all the host data
        # FIXME: HYD-1120: should do this part in parallel
        host_data = {}
        for host in ManagedHost.objects.filter(id__in = kwargs['host_ids']):
            with transaction.commit_on_success():
                self.log("Scanning server %s..." % host)
            data = self.invoke_agent(host, 'detect-scan')
            host_data[host] = data

        with transaction.commit_on_success():
            DetectScan(self).run(host_data)


class DetectTargetsJob(Job, HostListMixin):
    class Meta:
        app_label = 'chroma_core'

    def description(self):
        return "Scan for Lustre targets"

    def get_steps(self):
        return [(DetectTargetsStep, {'host_ids': [h.id for h in self.hosts.all()]})]

    def get_deps(self):
        deps = []
        for host in self.hosts.all():
            deps.append(DependOn(host.lnetconfiguration, 'nids_known'))

        return DependAll(deps)


class StartLNetStep(Step):
    idempotent = True

    def run(self, kwargs):
        from chroma_core.models import ManagedHost
        host = ManagedHost.objects.get(id = kwargs['host_id'])
        self.invoke_agent(host, "start-lnet")


class StopLNetStep(Step):
    idempotent = True

    def run(self, kwargs):
        from chroma_core.models import ManagedHost
        host = ManagedHost.objects.get(id = kwargs['host_id'])
        self.invoke_agent(host, "stop-lnet")


class LoadLNetStep(Step):
    idempotent = True

    def run(self, kwargs):
        from chroma_core.models import ManagedHost
        host = ManagedHost.objects.get(id = kwargs['host_id'])
        self.invoke_agent(host, "load-lnet")


class UnloadLNetStep(Step):
    idempotent = True

    def run(self, kwargs):
        from chroma_core.models import ManagedHost
        host = ManagedHost.objects.get(id = kwargs['host_id'])
        self.invoke_agent(host, "unload-lnet")


class LoadLNetJob(StateChangeJob):
    state_transition = (ManagedHost, 'lnet_unloaded', 'lnet_down')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)
    state_verb = 'Load LNet'

    class Meta:
        app_label = 'chroma_core'

    def description(self):
        return "Load LNet module on %s" % self.host

    def get_steps(self):
        return [(LoadLNetStep, {'host_id': self.host.id})]


class UnloadLNetJob(StateChangeJob):
    state_transition = (ManagedHost, 'lnet_down', 'lnet_unloaded')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)
    state_verb = 'Unload LNet'

    class Meta:
        app_label = 'chroma_core'

    def description(self):
        return "Unload LNet module on %s" % self.host

    def get_steps(self):
        return [(UnloadLNetStep, {'host_id': self.host.id})]


class StartLNetJob(StateChangeJob):
    state_transition = (ManagedHost, 'lnet_down', 'lnet_up')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)
    state_verb = 'Start LNet'

    class Meta:
        app_label = 'chroma_core'

    def description(self):
        return "Start LNet on %s" % self.host

    def get_steps(self):
        return [(StartLNetStep, {'host_id': self.host.id})]


class StopLNetJob(StateChangeJob):
    state_transition = (ManagedHost, 'lnet_up', 'lnet_down')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)
    state_verb = 'Stop LNet'

    class Meta:
        app_label = 'chroma_core'

    def description(self):
        return "Stop LNet on %s" % self.host

    def get_steps(self):
        return [(StopLNetStep, {'host_id': self.host.id})]


class DeleteHostStep(Step):
    idempotent = True

    def run(self, kwargs):
        from chroma_core.models import StorageResourceRecord
        from chroma_core.services.plugin_runner.agent_daemon_interface import AgentDaemonRpcInterface
        try:
            AgentDaemonRpcInterface().remove_host_resources(kwargs['host_id'])
        except StorageResourceRecord.DoesNotExist:
            # This is allowed, to account for the case where we submit the request_remove_resource,
            # then crash, then get restarted.
            pass

        from chroma_core.models import ManagedHost, AgentSession
        ManagedHost.delete(kwargs['host_id'])
        AgentSession.objects.filter(host = kwargs['host_id']).delete()
        if kwargs['force']:
            ManagedHost._base_manager.filter(id = kwargs['host_id']).update(state = 'removed')


class RemoveHostJob(StateChangeJob):
    state_transition = (ManagedHost, ['unconfigured', 'configured', 'lnet_up', 'lnet_down', 'lnet_unloaded'], 'removed')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)
    state_verb = 'Remove'

    requires_confirmation = True

    class Meta:
        app_label = 'chroma_core'

    def description(self):
        return "Remove host %s from configuration" % self.host

    def get_steps(self):
        return [(RemoveServerConfStep, {'host_id': self.host.id}),
                (UnconfigureNTPStep, {'host_id': self.host.id}),
                (UnconfigureRsyslogStep, {'host_id': self.host.id}),
            (DeleteHostStep, {'host_id': self.host.id, 'force': False})]


def _get_host_dependents(host):
    from chroma_core.models.target import ManagedTarget

    targets = set(list(ManagedTarget.objects.filter(managedtargetmount__host = host).distinct()))
    filesystems = set()
    for t in targets:
        t = t.downcast()
        if hasattr(t, 'filesystem'):
            filesystems.add(t.filesystem)
        elif hasattr(t, 'managedfilesystem_set'):
            for f in t.managedfilesystem_set.all():
                filesystems.add(f)
    for f in filesystems:
        for t in f.get_targets():
            targets.add(t)

    return targets, filesystems


class DeleteHostDependents(Step):
    idempotent = True

    def run(self, kwargs):
        host = ManagedHost.objects.get(pk = kwargs['host_id'])
        targets, filesystems = _get_host_dependents(host)

        job_log.info("DeleteHostDependents(%s): targets: %s, filesystems: %s" % (host, targets, filesystems))

        for object in itertools.chain(targets, filesystems):
            # We are allowed to modify state directly because we have locked these objects
            object.set_state('removed')
            object.save()
            object.__class__.delete(object.id)


class ForceRemoveHostJob(AdvertisedJob):
    host = models.ForeignKey(ManagedHost)

    requires_confirmation = True

    classes = ['ManagedHost']

    verb = "Force Remove"

    class Meta:
        app_label = 'chroma_core'

    def create_locks(self):
        locks = super(ForceRemoveHostJob, self).create_locks()

        locks.append(StateLock(
            job = self,
            locked_item = self.host,
            begin_state = None,
            end_state = 'removed',
            write = True
        ))

        targets, filesystems = _get_host_dependents(self.host)
        # Take a write lock on get_stateful_object if this is a StateChangeJob
        for object in itertools.chain(targets, filesystems):
            locks.append(StateLock(
                job = self,
                locked_item = object,
                begin_state = None,
                end_state = 'removed',
                write = True))

        return locks

    @classmethod
    def get_args(cls, host):
        return {'host_id': host.id}

    def description(self):
        return "Force remove host %s from configuration" % self.host

    def get_deps(self):
        return DependOn(self.host, 'configured', acceptable_states=self.host.not_state('removed'))

    def get_steps(self):
        return [(DeleteHostDependents, {'host_id': self.host.id}),
                (DeleteHostStep, {'host_id': self.host.id, 'force': True})]

    @classmethod
    def get_confirmation(cls, instance):
        return """The record for the server in Chroma Manager is removed without
attempting to contact the server. Any targets that depend on this server will
also be removed without any attempt to unconfigure them. This action should only
be used if the server is permanently unavailable."""


class RemoveUnconfiguredHostJob(StateChangeJob):
    state_transition = (ManagedHost, 'unconfigured', 'removed')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)
    state_verb = 'Remove'

    class Meta:
        app_label = 'chroma_core'

    def description(self):
        return "Remove host %s from configuration" % self.host

    def get_steps(self):
        return [(DeleteHostStep, {'host_id': self.host.id, 'force': False})]


class RelearnNidsJob(Job, HostListMixin):
    def description(self):
        return "Relearn NIDS on hosts %s" % ",".join([h.fqdn for h in self.hosts.all()])

    def get_deps(self):
        deps = []
        for host in self.hosts.all():
            deps.append(DependOn(host, "lnet_up"))
            deps.append(DependOn(host.lnetconfiguration, 'nids_known'))
        return DependAll(deps)

    def get_steps(self):
        return [
            (LearnNidsStep, {'host_id': host.id})
            for host in self.hosts.all()]

    class Meta:
        app_label = 'chroma_core'


class WriteConfStep(Step):
    def run(self, args):
        from chroma_core.models.target import ManagedTarget, FilesystemMember

        target = ManagedTarget.objects.get(pk = args['target_id']).downcast()
        primary_tm = target.managedtargetmount_set.get(primary = True)
        # tunefs.lustre --erase-param --mgsnode=<new_nid(s)> --writeconf /dev/..

        agent_args = {
            'writeconf': True,
            'erase_params': True,
            'device': primary_tm.volume_node.path}

        if isinstance(target, FilesystemMember):
            agent_args['mgsnode'] = tuple(target.filesystem.mgs.nids()[0:1])

        fail_nids = target.get_failover_nids()
        if fail_nids:
            agent_args['failnode'] = fail_nids
        self.invoke_agent(primary_tm.host, "writeconf-target", agent_args)


class ResetConfParamsStep(Step):
    def run(self, args):
        from chroma_core.models.target import ManagedMgs

        # Reset version to zero so that next time the target is started
        # it will write all its parameters from chroma to lustre.
        ManagedMgs.objects.filter(pk = args['mgt_id']).update(conf_param_version_applied = 0)


class UpdateNidsJob(Job, HostListMixin):
    def description(self):
        if self.hosts.count() > 1:
            return "Update NIDs on %d hosts" % self.hosts.count()
        else:
            return "Update NIDS on host %s" % self.hosts.all()[0]

    def _targets_on_hosts(self):
        from chroma_core.models.target import ManagedMgs, ManagedTarget, FilesystemMember
        targets = ManagedTarget.objects.filter(managedtargetmount__host__in = self.hosts.all())
        targets = [t.downcast() for t in targets]

        filesystems = set()
        for target in targets:
            if isinstance(target, FilesystemMember):
                filesystems.add(target.filesystem)

            if isinstance(target, ManagedMgs):
                for fs in target.managedfilesystem_set.all():
                    filesystems.add(fs)

        return filesystems, targets

    def get_deps(self):
        filesystems, targets = self._targets_on_hosts()

        target_hosts = set()
        target_primary_hosts = set()
        for target in targets:
            for mtm in target.managedtargetmount_set.all():
                if mtm.primary:
                    target_primary_hosts.add(mtm.host)
                target_hosts.add(mtm.host)

        return DependAll(
            [DependOn(host, 'lnet_up') for host in target_primary_hosts]
            + [DependOn(host.lnetconfiguration, 'nids_known') for host in target_hosts]
            + [DependOn(fs, 'stopped') for fs in filesystems]
            + [DependOn(t, 'unmounted') for t in targets]
        )

    def get_steps(self):
        from chroma_core.models.target import ManagedMgs
        filesystems, targets = self._targets_on_hosts()
        all_targets = set()
        for fs in filesystems:
            all_targets |= set(fs.get_targets())
        all_targets |= set(targets)

        steps = []
        for target in all_targets:
            target = target.downcast()
            steps.append((WriteConfStep, {'target_id': target.id}))

        for target in all_targets:
            target = target.downcast()
            if isinstance(target, ManagedMgs):
                steps.append((ResetConfParamsStep, {'mgt_id': target.id}))

        for target in all_targets:
            if isinstance(target, ManagedMgs):
                from chroma_core.models.target import MountStep
                steps.append((MountStep, {'target_id': target.id}))

        # FIXME: HYD-1133: when doing this properly these should
        # be run as parallel jobs
        for target in all_targets:
            if not isinstance(target, ManagedMgs):
                from chroma_core.models.target import MountStep
                steps.append((MountStep, {'target_id': target.id}))

        for target in all_targets:
            if not isinstance(target, ManagedMgs):
                from chroma_core.models.target import UnmountStep
                steps.append((UnmountStep, {'target_id': target.id}))

        for target in all_targets:
            if isinstance(target, ManagedMgs):
                from chroma_core.models.target import UnmountStep
                steps.append((UnmountStep, {'target_id': target.id}))

        # FIXME: HYD-1133: should be marking targets as unregistered
        # so that they get started in the correct order next time
        # NB in that case also need to ensure that the start
        # of all the targets happens before StateManager calls
        # the completion hook that tries to apply configuration params
        # for targets that haven't been set up yet.

        return steps

    class Meta:
        app_label = 'chroma_core'


class HostContactAlert(AlertState):
    def message(self):
        return "Lost contact with host %s" % self.alert_item

    class Meta:
        app_label = 'chroma_core'

    def begin_event(self):
        return AlertEvent(
            message_str = "Lost contact with host %s" % self.alert_item,
            host = self.alert_item,
            alert = self,
            severity = logging.WARNING)

    def end_event(self):
        return AlertEvent(
            message_str = "Re-established contact with host %s" % self.alert_item,
            host = self.alert_item,
            alert = self,
            severity = logging.INFO)


class LNetOfflineAlert(AlertState):
    def message(self):
        return "LNet offline on server %s" % self.alert_item

    class Meta:
        app_label = 'chroma_core'

    def begin_event(self):
        return AlertEvent(
            message_str = "LNet stopped on server '%s'" % self.alert_item,
            host = self.alert_item,
            alert = self,
            severity = logging.WARNING)

    def end_event(self):
        return AlertEvent(
            message_str = "LNet started on server '%s'" % self.alert_item,
            host = self.alert_item,
            alert = self,
            severity = logging.INFO)


class LNetNidsChangedAlert(AlertState):
    def message(self):
        return "NIDs changed on server %s" % self.alert_item

    class Meta:
        app_label = 'chroma_core'

    def begin_event(self):
        return AlertEvent(
            message_str = "LNet NIDs changed on server %s" % self.alert_item,
            host = self.alert_item,
            alert = self,
            severity = logging.WARNING)

    def end_event(self):
        return AlertEvent(
            message_str = "LNet NIDs updated for server %s" % self.alert_item,
            host = self.alert_item,
            alert = self,
            severity = logging.INFO)


class NoLNetInfo(Exception):
    pass
