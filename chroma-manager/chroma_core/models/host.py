#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import datetime
import logging
import dateutil.parser

from django.db import models
from django.db import transaction
from django.db import IntegrityError
import itertools
from django.db.models.aggregates import Max, Count
from django.db.models.query_utils import Q
from chroma_core.lib.cache import ObjectCache
from chroma_core.models import StateChangeJob
from chroma_core.models.alert import AlertState
from chroma_core.models.event import AlertEvent

from chroma_core.models.utils import WorkaroundDateTimeField
from chroma_core.models.jobs import StatefulObject, Job, AdvertisedJob, StateLock
from chroma_core.lib.job import  DependOn, DependAll, Step
from chroma_core.models.utils import MeasuredEntity, DeletableDowncastableMetaclass, DeletableMetaclass

from chroma_core.lib.job import job_log

import settings


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

    # TODO: separate the LNET state [unloaded, down, up] from the host state [created, removed]
    states = ['unconfigured', 'lnet_unloaded', 'lnet_down', 'lnet_up', 'removed']
    initial_state = 'unconfigured'

    last_contact = WorkaroundDateTimeField(blank = True, null = True, help_text = "When the Chroma agent on this host last sent an update to this server")

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
            time_since = datetime.datetime.utcnow() - self.last_contact
            return time_since <= datetime.timedelta(seconds=settings.AUDIT_PERIOD * 2)

    @classmethod
    def create_from_string(cls, address_string, start_lnet = True):
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

        if start_lnet:
            # Attempt some initial setup jobs
            from chroma_core.models.jobs import Command
            command = Command.set_state([(host, 'lnet_unloaded'), (lnet_configuration, 'nids_known')], "Setting up host %s" % address_string)
        else:
            command = None

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
            roles.add(target.role())

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
    storage_resource = models.ForeignKey('StorageResourceRecord', blank = True, null = True)

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
            raise ValueError("Nids not known yet for host %s" % self.host)
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

        job_log.debug("LearnNidsStep(%s): %s" % (host, result))

        nids = []
        for nid_string in result:
            nid, created = Nid.objects.get_or_create(
                    lnet_configuration = host.lnetconfiguration,
                    nid_string = normalize_nid(nid_string))
            if created:
                job_log.debug("LearnNidsStep(%s): learned new nid %s" % (host, nid.nid_string))
            nids.append(nid)

        for old_nid in Nid.objects.filter(~Q(id__in = [n.id for n in nids]), lnet_configuration = host.lnetconfiguration):
            job_log.debug("LearnNidsStep(%s): removed old nid %s" % (host, old_nid.nid_string))
            old_nid.delete()


class ConfigureLNetJob(StateChangeJob):
    state_transition = (LNetConfiguration, 'nids_unknown', 'nids_known')
    stateful_object = 'lnet_configuration'
    lnet_configuration = models.ForeignKey(LNetConfiguration)
    state_verb = 'Configure LNet'

    def description(self):
        return "Configuring LNet on %s" % self.lnet_configuration.host

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
        try:
            self.invoke_agent(host, "configure-rsyslog --node %s" % fqdn)
        except RuntimeError, e:
            # FIXME: Would be smarter to detect capabilities before
            # trying to run things which may break.  Don't want to do it
            # every time, though, because it adds an extra round trip for
            # every step.  Maybe we should serialize the audited
            # capabilities in a new ManagedHost field? (HYD-638)
            from chroma_core.lib.job import job_log
            job_log.error("Failed to configure rsyslog on %s: %s" % (host, e))


class UnconfigureRsyslogStep(Step):
    idempotent = True

    def run(self, kwargs):
        from chroma_core.models import ManagedHost
        host = ManagedHost.objects.get(id = kwargs['host_id'])
        self.invoke_agent(host, "unconfigure-rsyslog")


class LearnHostnameStep(Step):
    idempotent = True

    def run(self, kwargs):
        from chroma_core.lib.job import job_log

        from chroma_core.models import ManagedHost
        host = ManagedHost.objects.get(id = kwargs['host_id'])
        fqdn = self.invoke_agent(host, "get-fqdn")
        nodename = self.invoke_agent(host, "get-nodename")
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
        # Get the device-scan output
        from chroma_core.models import ManagedHost, AgentSession
        host = ManagedHost.objects.get(id = kwargs['host_id'])
        updates = self.invoke_agent(host, "device-plugin")
        try:
            del updates['lustre']
        except KeyError:
            pass

        # Fake a session as if the agent had reported in
        from chroma_core.lib.storage_plugin import messaging
        session, created = AgentSession.objects.get_or_create(host = host)
        messaging.simple_send('agent', {
                    "session_id": session.session_id,
                    "host_id": host.id,
                    "updates": updates
            })

        from chroma_core.lib.storage_plugin.daemon import AgentDaemonRpc
        AgentDaemonRpc().await_session(kwargs['host_id'])


class CheckClockStep(Step):
    idempotent = True

    def run(self, kwargs):
        # Get the device-scan output
        from chroma_core.models import ManagedHost
        host = ManagedHost.objects.get(id = kwargs['host_id'])
        agent_time_str = self.invoke_agent(host, "get-time")
        agent_time = dateutil.parser.parse(agent_time_str)

        # Get a tz-aware datetime object
        server_time = datetime.datetime.utcnow()
        from dateutil import tz
        server_time = server_time.replace(tzinfo=tz.tzutc())

        if agent_time > server_time:
            if (agent_time - server_time) > datetime.timedelta(seconds = settings.AGENT_CLOCK_TOLERANCE):
                raise RuntimeError("Host %s clock is fast.  agent time %s, server time %s" % (host, agent_time, server_time))

        if server_time > agent_time:
            if (server_time - agent_time) > datetime.timedelta(seconds = settings.AGENT_CLOCK_TOLERANCE):
                raise RuntimeError("Host %s clock is slow.  agent time %s, server time %s" % (host, agent_time, server_time))


class SetupHostJob(StateChangeJob):
    state_transition = (ManagedHost, 'unconfigured', 'lnet_unloaded')
    stateful_object = 'managed_host'
    managed_host = models.ForeignKey(ManagedHost)
    state_verb = 'Set up server'

    def description(self):
        return "Setting up server %s" % self.managed_host

    def get_steps(self):
        return [(LearnHostnameStep, {'host_id': self.managed_host.pk}),
                (ConfigureRsyslogStep, {'host_id': self.managed_host.pk}),
                (SetServerConfStep, {'host_id': self.managed_host.pk}),
                (CheckClockStep, {'host_id': self.managed_host.pk}),
                (LearnDevicesStep, {'host_id': self.managed_host.pk})]

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
        for host in ManagedHost.objects.all():
            data = self.invoke_agent(host, 'detect-scan')
            host_data[host] = data

        with transaction.commit_on_success():
            DetectScan().run(host_data)


class DetectTargetsJob(Job):
    # FIXME: HYD-XYZ this should take a list of hosts
    @property
    def hosts(self):
        return ManagedHost.objects

    class Meta:
        app_label = 'chroma_core'

    def description(self):
        return "Scanning for Lustre targets"

    def get_steps(self):
        return [(DetectTargetsStep, {})]

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
        return "Loading LNet module on %s" % self.host

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
        return "Unloading LNet module on %s" % self.host

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
        from chroma_core.lib.storage_plugin.daemon import AgentDaemonRpc
        try:
            AgentDaemonRpc().remove_host_resources(kwargs['host_id'])
        except StorageResourceRecord.DoesNotExist:
            # This is allowed, to account for the case where we submit the request_remove_resource,
            # then crash, then get restarted.
            pass

        from chroma_core.models import ManagedHost
        ManagedHost.delete(kwargs['host_id'])


class RemoveHostJob(StateChangeJob):
    state_transition = (ManagedHost, ['unconfigured', 'lnet_up', 'lnet_down', 'lnet_unloaded'], 'removed')
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
            (DeleteHostStep, {'host_id': self.host.id})]


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

        from chroma_core.lib.job import job_log
        job_log.info("DeleteHostDependents(%s): targets: %s, filesystems: %s" % (host, targets, filesystems))

        for object in itertools.chain(targets, filesystems):
            # We are allowed to modify state directly because
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
            begin_state = "",
            end_state = 'removed',
            write = True
        ))

        targets, filesystems = _get_host_dependents(self.host)
        # Take a write lock on get_stateful_object if this is a StateChangeJob
        for object in itertools.chain(targets, filesystems):
            locks.append(StateLock(
                job = self,
                locked_item = object,
                begin_state = "",
                end_state = 'removed',
                write = True))

        return locks

    @classmethod
    def get_args(cls, host):
        return {'host_id': host.id}

    def description(self):
        return "Force remove host %s from configuration" % self.host

    def get_steps(self):
        return [(DeleteHostDependents, {'host_id': self.host.id}),
                (DeleteHostStep, {'host_id': self.host.id})]

    @classmethod
    def get_confirmation(cls, instance):
        return """Force-removing a server will cause Chroma to remove records of that server
without attempting to contact the server.  Any targets which depend on this server will also
be removed without any attempt to un-configure them.  This action should only be used if
the server is permanently unavailable."""


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
        return [(DeleteHostStep, {'host_id': self.host.id})]


class RelearnNidsJob(Job):
    host = models.ForeignKey('ManagedHost')

    def description(self):
        return "Relearning NIDS on host %s" % self.host

    def get_deps(self):
        return DependAll([
            DependOn(self.host, "lnet_up"),
            DependOn(self.host.lnetconfiguration, 'nids_known')
            ])

    def get_steps(self):
        return [(LearnNidsStep, {'host_id': self.host.id})]

    class Meta:
        app_label = 'chroma_core'


class WriteConfStep(Step):
    def run(self, args):
        from chroma_core.models.target import ManagedTarget

        target = ManagedTarget.objects.get(pk = args['target_id']).downcast()
        primary_tm = target.managedtargetmount_set.get(primary = True)
        # tunefs.lustre --erase-param --mgsnode=<new_nid(s)> --writeconf /dev/..

        agent_args = {
            'writeconf': True,
            'erase_params': True,
            'mgsnode': tuple(primary_tm.host.lnetconfiguration.get_nids()),
            'device': primary_tm.volume_node.path}
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


class UpdateNidsJob(Job):
    # FIXME: HYD-XYZ this should take a list of hosts
    # as an argument: doing m2m attributes of Jobs
    # is painful atm because:
    # * constructor in command_run_jobs doesn't know how to deal with them
    # * assigning them requires model to be saved first, which means
    #   we can't e.g. check deps before saving job
    @property
    def hosts(self):
        return ManagedHost.objects

    def description(self):
        if self.hosts.count() > 1:
            return "Updating NIDs on %d hosts" % self.hosts.count()
        else:
            return "Updating NIDS on host %s" % self.hosts.all()[0]

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

        return DependAll(
            [DependOn(fs, 'stopped') for fs in filesystems]
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
