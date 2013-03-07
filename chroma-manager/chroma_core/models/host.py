#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import json
import logging
import itertools

from django.db import models
from django.db import transaction
from django.db import IntegrityError

from django.db.models.aggregates import Aggregate, Count
from django.db.models.sql import aggregates as sql_aggregates

from django.db.models.query_utils import Q

from chroma_core.lib.util import normalize_nid
from chroma_core.lib.cache import ObjectCache
from chroma_core.models.jobs import StateChangeJob
from chroma_core.models.event import Event
from chroma_core.models.alert import AlertState
from chroma_core.models.event import AlertEvent
from chroma_core.models.jobs import StatefulObject, Job, AdvertisedJob, StateLock
from chroma_core.lib.job import job_log
from chroma_core.lib.job import  DependOn, DependAll, Step
from chroma_core.models.utils import MeasuredEntity, DeletableDowncastableMetaclass, DeletableMetaclass

import settings


# Max() worked on mysql's NullBooleanField because the DB value is stored
# in a TINYINT.  pgsql uses an actual boolean field type, so Max() won't
# work.  bool_or() seems to be the moral equivalent.
# http://www.postgresql.org/docs/8.4/static/functions-aggregate.html
class BoolOr(Aggregate):
    name = 'BoolOr'

    def _default_alias(self):
        return '%s__bool_or' % self.lookup


# Unfortunately, we have to do a bit of monkey-patching to make this
# work cleanly.
class SqlBoolOr(sql_aggregates.Aggregate):
    sql_function = 'BOOL_OR'
sql_aggregates.BoolOr = SqlBoolOr


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


class ClientCertificate(models.Model):
    host = models.ForeignKey('ManagedHost')
    serial = models.CharField(max_length = 16)
    revoked = models.BooleanField(default = False)

    class Meta:
        app_label = 'chroma_core'


class ManagedHost(DeletableStatefulObject, MeasuredEntity):
    address = models.CharField(max_length = 255, help_text = "A URI like 'user@myhost.net:22'")

    # A fully qualified domain name like flint02.testnet
    fqdn = models.CharField(max_length = 255, help_text = "Unicode string, fully qualified domain name")

    # a nodename to match against fqdn in corosync output
    nodename = models.CharField(max_length = 255, help_text = "Unicode string, node name")

    # The last known boot time
    boot_time = models.DateTimeField(null = True, blank = True)

    # Up from the point of view of a peer in the corosync cluster for this node
    corosync_reported_up = models.BooleanField(default=False,
                                               help_text="True if corosync "
                                                         "on a node in "
                                                         "this node's cluster "
                                                         "reports that this "
                                                         "node is online")

    # FIXME: HYD-1215: separate the LNET state [unloaded, down, up] from the host state [created, removed]
    states = ['unconfigured', 'configured', 'lnet_unloaded', 'lnet_down', 'lnet_up', 'removed']
    initial_state = 'unconfigured'

    class Meta:
        app_label = 'chroma_core'
        unique_together = ('address',)
        ordering = ['id']

    def __str__(self):
        return self.get_label()

    def get_label(self):
        """Return the FQDN if it is known, else the address"""
        name = self.fqdn

        if name.endswith(".localdomain"):
            name = name[:-len(".localdomain")]

        return name

    def save(self, *args, **kwargs):
        try:
            ManagedHost.objects.get(~Q(pk = self.pk), fqdn = self.fqdn)
            raise IntegrityError("FQDN %s in use" % self.fqdn)
        except ManagedHost.DoesNotExist:
            pass

        super(ManagedHost, self).save(*args, **kwargs)

    def get_available_states(self, begin_state):
        if self.immutable_state:
            if begin_state == 'unconfigured':
                return ['removed', 'configured']
            else:
                return ['removed']
        else:
            return super(ManagedHost, self).get_available_states(begin_state)

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
        ordering = ['id']

    @classmethod
    def get_unused_luns(cls, queryset = None):
        """Get all Luns which are not used by Targets"""
        if not queryset:
            queryset = cls.objects.all()

        queryset = queryset.annotate(any_targets = BoolOr('volumenode__managedtargetmount__target__not_deleted'))
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
                    any_targets = BoolOr('volumenode__managedtargetmount__target__not_deleted'),
                    has_primary = BoolOr('volumenode__primary'),
                    num_volumenodes = Count('volumenode')
                ).filter((Q(num_volumenodes = 1) | Q(has_primary = True)) & Q(any_targets = None))

    def get_kind(self):
        if not hasattr(self, 'kind'):
            self.kind = self._get_kind()

        return self.kind

    def _get_kind(self):
        """:return: A string or unicode string which is a human readable noun corresponding
        to the class of storage e.g. LVM LV, Linux partition, iSCSI LUN"""
        if not self.storage_resource:
            return "Unknown"

        resource_klass = self.storage_resource.to_resource_class()
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

        return self.storage_resource.alias_or_name()

    def save(self, *args, **kwargs):
        self.label = self._get_label()
        self.kind = self._get_kind()
        super(Volume, self,).save(*args, **kwargs)

    @staticmethod
    def ha_status_label(volumenode_count, primary_count, failover_count):
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

    primary = models.BooleanField(default = False, help_text = "If ``true``, this node will\
            be used for the primary Lustre server when creating a target")

    use = models.BooleanField(default = True, help_text = "If ``true``, this node will \
            be used as a Lustre server when creating a target (if primary is not set,\
            this node will be used as a secondary server)")

    class Meta:
        unique_together = ('host', 'path')
        app_label = 'chroma_core'
        ordering = ['id']

    def __str__(self):
        return "%s:%s" % (self.host, self.path)


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
        ordering = ['id']


class Nid(models.Model):
    """Simplified NID representation for those we detect already-configured"""
    lnet_configuration = models.ForeignKey(LNetConfiguration)
    nid_string = models.CharField(max_length=128)

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']


class LearnNidsStep(Step):
    idempotent = True
    database = True

    def run(self, kwargs):
        from chroma_core.models import Nid

        host = kwargs['host']
        result = self.invoke_agent(host, "lnet_scan")

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
        return [(LearnNidsStep, {'host': self.lnet_configuration.host})]

    def get_deps(self):
        return DependOn(ObjectCache.get_one(ManagedHost, lambda mh: mh.id == self.lnet_configuration.host_id), "lnet_up")

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']


class ConfigureRsyslogStep(Step):
    idempotent = True

    def run(self, kwargs):
        host = kwargs['host']
        if not host.immutable_state:
            self.invoke_agent(host, "configure_rsyslog")


class ConfigureNTPStep(Step):
    idempotent = True

    def run(self, kwargs):
        if settings.NTP_SERVER_HOSTNAME:
            ntp_server = settings.NTP_SERVER_HOSTNAME
        else:
            import socket
            ntp_server = socket.getfqdn()

        host = kwargs['host']
        if not host.immutable_state:
            self.invoke_agent(host, "configure_ntp", {'ntp_server': ntp_server})


class UnconfigureRsyslogStep(Step):
    idempotent = True

    def run(self, kwargs):
        host = kwargs['host']
        if not host.immutable_state:
            self.invoke_agent(host, "unconfigure_rsyslog")


class UnconfigureNTPStep(Step):
    idempotent = True

    def run(self, kwargs):
        host = kwargs['host']
        if not host.immutable_state:
            self.invoke_agent(host, "unconfigure_ntp")


class GetLNetStateStep(Step):
    idempotent = True

    # FIXME: using database=True to do the alerting update inside .set_state but
    # should do it in a completion
    database = True

    def run(self, kwargs):
        host = kwargs['host']

        lustre_data = self.invoke_agent(host, "device_plugin", {'plugin': 'lustre'})['lustre']

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
        ordering = ['id']

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
        return {'host': host}

    def description(self):
        return "Get LNet state for %s" % self.host

    def get_steps(self):
        return [(GetLNetStateStep, {'host': self.host})]


class RemoveServerConfStep(Step):
    idempotent = True

    def run(self, kwargs):
        host = kwargs['host']
        self.invoke_agent(host, "deregister_server")


class LearnDevicesStep(Step):
    idempotent = True

    # Require database to talk to storage_plugin_manager
    database = True

    def run(self, kwargs):
        from chroma_core.services.plugin_runner.agent_daemon_interface import AgentDaemonRpcInterface
        from chroma_core.services.job_scheduler.agent_rpc import AgentException

        # Get the device-scan output
        host = kwargs['host']

        plugin_data = {}
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager
        for plugin in storage_plugin_manager.loaded_plugin_names:
            try:
                plugin_data[plugin] = self.invoke_agent(host, "device_plugin", {'plugin': plugin})[plugin]
            except AgentException:
                self.log("No data for plugin %s from host %s" % (plugin, host))

        AgentDaemonRpcInterface().setup_host(host.id, plugin_data)


class SetupHostJob(StateChangeJob):
    state_transition = (ManagedHost, 'unconfigured', 'configured')
    stateful_object = 'managed_host'
    managed_host = models.ForeignKey(ManagedHost)
    state_verb = 'Set up server'

    def description(self):
        return "Set up server %s" % self.managed_host

    def get_steps(self):
        return [(ConfigureNTPStep, {'host': self.managed_host}),
               (ConfigureRsyslogStep, {'host': self.managed_host}),
                (LearnDevicesStep, {'host': self.managed_host})]

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']


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
        ordering = ['id']


class DetectTargetsStep(Step):
    database = True

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
            data = self.invoke_agent(host, 'detect_scan')
            host_data[host] = data

        with transaction.commit_on_success():
            DetectScan(self).run(host_data)


class DetectTargetsJob(Job, HostListMixin):
    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

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
        host = kwargs['host']
        self.invoke_agent(host, "start_lnet")


class StopLNetStep(Step):
    idempotent = True

    def run(self, kwargs):
        host = kwargs['host']
        self.invoke_agent(host, "stop_lnet")


class LoadLNetStep(Step):
    idempotent = True

    def run(self, kwargs):
        host = kwargs['host']
        self.invoke_agent(host, "load_lnet")


class UnloadLNetStep(Step):
    idempotent = True

    def run(self, kwargs):
        host = kwargs['host']
        self.invoke_agent(host, "unload_lnet")


class LoadLNetJob(StateChangeJob):
    state_transition = (ManagedHost, 'lnet_unloaded', 'lnet_down')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)
    state_verb = 'Load LNet'

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    def description(self):
        return "Load LNet module on %s" % self.host

    def get_steps(self):
        return [(LoadLNetStep, {'host': self.host})]


class UnloadLNetJob(StateChangeJob):
    state_transition = (ManagedHost, 'lnet_down', 'lnet_unloaded')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)
    state_verb = 'Unload LNet'

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    def description(self):
        return "Unload LNet module on %s" % self.host

    def get_steps(self):
        return [(UnloadLNetStep, {'host': self.host})]


class StartLNetJob(StateChangeJob):
    state_transition = (ManagedHost, 'lnet_down', 'lnet_up')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)
    state_verb = 'Start LNet'

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    def description(self):
        return "Start LNet on %s" % self.host

    def get_steps(self):
        return [(StartLNetStep, {'host': self.host})]


class StopLNetJob(StateChangeJob):
    state_transition = (ManagedHost, 'lnet_up', 'lnet_down')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)
    state_verb = 'Stop LNet'

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    def description(self):
        return "Stop LNet on %s" % self.host

    def get_steps(self):
        return [(StopLNetStep, {'host': self.host})]


class DeleteHostStep(Step):
    idempotent = True
    database = True

    def run(self, kwargs):
        from chroma_core.services.http_agent import HttpAgentRpc
        from chroma_core.services.job_scheduler.agent_rpc import AgentRpc

        host = kwargs['host']
        # First, cut off any more incoming connections
        # TODO: populate a CRL and do an apachectl graceful to reread it

        # Second, terminate any currently open connections and ensure there is nothing in a queue
        # which will be drained into AMQP
        HttpAgentRpc().remove_host(host.fqdn)

        # Third, for all receivers of AMQP messages from originating from hosts, ask them to
        # drain their queues, discarding any messages from the host being removed
        # ... or if we could get a bit of info from rabbitmq we could look at how many N messages
        # are pending in a queue, then track its 'messages consumed' count (if such a count exists)
        # until N + 1 messages have been consumed
        # TODO
        # The last receiver of AMQP messages to clean up is myself (JobScheduler, inside which
        # this code will execute)
        AgentRpc.remove(host.fqdn)

        from chroma_core.models import StorageResourceRecord
        from chroma_core.services.plugin_runner.agent_daemon_interface import AgentDaemonRpcInterface
        try:
            AgentDaemonRpcInterface().remove_host_resources(host.id)
        except StorageResourceRecord.DoesNotExist:
            # This is allowed, to account for the case where we submit the request_remove_resource,
            # then crash, then get restarted.
            pass

        host.mark_deleted()
        if kwargs['force']:
            host.state = 'removed'


class RemoveHostJob(StateChangeJob):
    state_transition = (ManagedHost, ['unconfigured', 'configured', 'lnet_up', 'lnet_down', 'lnet_unloaded'], 'removed')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)
    state_verb = 'Remove'

    requires_confirmation = True

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    def description(self):
        return "Remove host %s from configuration" % self.host

    def get_steps(self):
        return [(UnconfigureNTPStep, {'host': self.host}),
                (UnconfigureRsyslogStep, {'host': self.host}),
                (RemoveServerConfStep, {'host': self.host}),
                (DeleteHostStep, {'host': self.host, 'force': False})]


def _get_host_dependents(host):
    from chroma_core.models.target import ManagedTarget, ManagedMgs, FilesystemMember

    targets = set(list(ManagedTarget.objects.filter(managedtargetmount__host = host).distinct()))
    filesystems = set()
    for t in targets:
        if not t.__class__ == ManagedTarget:
            job_log.debug("objects=%s %s" % (ManagedTarget.objects, ManagedTarget.objects.__class__))
            raise RuntimeError("Seems to have given DowncastMetaClass behaviour")
        if issubclass(t.downcast_class, FilesystemMember):
            filesystems.add(t.downcast().filesystem)
        elif issubclass(t.downcast_class, ManagedMgs):
            for f in t.downcast().managedfilesystem_set.all():
                filesystems.add(f)
    for f in filesystems:
        targets |= set(list(f.get_targets()))

    return targets, filesystems


class DeleteHostDependents(Step):
    idempotent = True
    database = True

    def run(self, kwargs):
        host = kwargs['host']
        targets, filesystems = _get_host_dependents(host)

        job_log.info("DeleteHostDependents(%s): targets: %s, filesystems: %s" % (host, targets, filesystems))

        for object in itertools.chain(targets, filesystems):
            # We are allowed to modify state directly because we have locked these objects
            object.set_state('removed')
            object.mark_deleted()
            object.save()


class ForceRemoveHostJob(AdvertisedJob):
    host = models.ForeignKey(ManagedHost)

    requires_confirmation = True

    classes = ['ManagedHost']

    verb = "Force Remove"

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

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
            job_log.debug("Creating StateLock on %s/%s" % (object.__class__, object.id))
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
        return [(DeleteHostDependents, {'host': self.host}),
                (DeleteHostStep, {'host': self.host, 'force': True})]

    @classmethod
    def get_confirmation(cls, instance):
        return """The record for the server in Chroma Manager is removed without
attempting to contact the server. Any targets that depend on this server will
also be removed without any attempt to unconfigure them. This action should only
be used if the server is permanently unavailable."""


class RebootHostJob(AdvertisedJob):
    host = models.ForeignKey(ManagedHost)

    requires_confirmation = True

    classes = ['ManagedHost']

    verb = "Reboot"

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    @classmethod
    def get_args(cls, host):
        return {'host_id': host.id}

    def description(self):
        return "Initiate a reboot on host %s" % self.host

    def get_deps(self):
        return DependOn(self.host, 'configured', acceptable_states=self.host.not_states(['removed', 'unconfigured']))

    def get_steps(self):
        return [(RebootHostStep, {'host': self.host})]

    @classmethod
    def get_confirmation(cls, instance):
        return """Initiate a reboot on the host. Any HA-capable targets running on the host will be failed over to a peer. Non-HA-capable targets will be unavailable until the host has finished rebooting."""


class RebootHostStep(Step):
    idempotent = True

    def run(self, kwargs):
        host = kwargs['host']
        self.invoke_agent(host, "reboot_server")

        self.log("Rebooted host %s" % host)


class ShutdownHostJob(AdvertisedJob):
    host = models.ForeignKey(ManagedHost)

    requires_confirmation = True

    classes = ['ManagedHost']

    verb = "Shutdown"

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    @classmethod
    def get_args(cls, host):
        return {'host_id': host.id}

    def description(self):
        return "Initiate an orderly shutdown on host %s" % self.host

    def get_deps(self):
        return DependOn(self.host, 'configured', acceptable_states=self.host.not_states(['removed', 'unconfigured']))

    def get_steps(self):
        return [(ShutdownHostStep, {'host': self.host})]

    @classmethod
    def get_confirmation(cls, instance):
        return """Initiate an orderly shutdown on the host. Any HA-capable targets running on the host will be failed over to a peer. Non-HA-capable targets will be unavailable until the host has been restarted."""


class ShutdownHostStep(Step):
    idempotent = True

    def run(self, kwargs):
        host = kwargs['host']
        self.invoke_agent(host, "shutdown_server")

        self.log("Shut down host %s" % host)


class RemoveUnconfiguredHostJob(StateChangeJob):
    state_transition = (ManagedHost, 'unconfigured', 'removed')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)
    state_verb = 'Remove'

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    def description(self):
        return "Remove host %s from configuration" % self.host

    def get_steps(self):
        return [(DeleteHostStep, {'host': self.host, 'force': False})]


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
            (LearnNidsStep, {'host': host})
            for host in self.hosts.all()]

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']


class WriteConfStep(Step):
    def run(self, args):
        from chroma_core.models.target import FilesystemMember

        target = args['target']

        agent_args = {
            'writeconf': True,
            'erase_params': True,
            'device': args['path']}

        if issubclass(target.downcast_class, FilesystemMember):
            agent_args['mgsnode'] = args['mgsnode']

        fail_nids = args['fail_nids']
        if fail_nids:
            agent_args['failnode'] = fail_nids
        self.invoke_agent(args['host'], "writeconf_target", agent_args)


class ResetConfParamsStep(Step):
    database = True

    def run(self, args):
        # Reset version to zero so that next time the target is started
        # it will write all its parameters from chroma to lustre.
        mgt = args['mgt']
        mgt.conf_param_version_applied = 0
        mgt.save()


class UpdateNidsJob(Job, HostListMixin):
    def description(self):
        if self.hosts.count() > 1:
            return "Update NIDs on %d hosts" % self.hosts.count()
        else:
            return "Update NIDS on host %s" % self.hosts.all()[0]

    def _targets_on_hosts(self):
        from chroma_core.models.target import ManagedMgs, ManagedTarget, FilesystemMember
        from chroma_core.models.filesystem import ManagedFilesystem

        filesystems = set()
        targets = []
        for target in ManagedTarget.objects.filter(managedtargetmount__host__in = self.hosts.all()):
            targets.append(target)
            if issubclass(target.downcast_class, FilesystemMember):
                # FIXME: N downcasts :-(
                filesystems.add(target.downcast().filesystem)

            if issubclass(target.downcast_class, ManagedMgs):
                for fs in target.downcast().managedfilesystem_set.all():
                    filesystems.add(fs)

        targets = [ObjectCache.get_by_id(ManagedTarget, t.id) for t in targets]
        filesystems = [ObjectCache.get_by_id(ManagedFilesystem, f.id) for f in filesystems]

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

    def create_locks(self):
        locks = []
        filesystems, targets = self._targets_on_hosts()

        for target in targets:
            locks.append(StateLock(
                job = self,
                locked_item = target,
                begin_state = "unmounted",
                end_state = "unmounted",
                write = True
            ))

        return locks

    def get_steps(self):
        from chroma_core.models.target import ManagedMgs
        from chroma_core.models.target import MountStep
        from chroma_core.models.target import UnmountStep
        from chroma_core.models.target import FilesystemMember

        filesystems, targets = self._targets_on_hosts()
        all_targets = set()
        for fs in filesystems:
            all_targets |= set(fs.get_targets())
        all_targets |= set(targets)

        steps = []
        for target in all_targets:
            target = target.downcast()
            primary_tm = target.managedtargetmount_set.get(primary = True)
            steps.append((WriteConfStep, {
                'target': target,
                'path': primary_tm.volume_node.path,
                'mgsnode': target.filesystem.mgs.nids() if issubclass(target.downcast_class, FilesystemMember) else None,
                'host': primary_tm.host,
                'fail_nids': target.get_failover_nids()
            }))

        mgs_targets = [t for t in targets if issubclass(t.downcast_class, ManagedMgs)]
        fs_targets = [t for t in targets if not issubclass(t.downcast_class, ManagedMgs)]

        for target in mgs_targets:
            steps.append((ResetConfParamsStep, {'mgt': target.downcast()}))

        for target in mgs_targets:
            steps.append((MountStep, {'target': target, "host": target.best_available_host()}))

        # FIXME: HYD-1133: when doing this properly these should
        # be run as parallel jobs
        for target in fs_targets:
            steps.append((MountStep, {'target': target, "host": target.best_available_host()}))

        for target in fs_targets:
            steps.append((UnmountStep, {'target': target, "host": target.best_available_host()}))

        for target in mgs_targets:
            steps.append((UnmountStep, {'target': target, "host": target.best_available_host()}))

        # FIXME: HYD-1133: should be marking targets as unregistered
        # so that they get started in the correct order next time
        # NB in that case also need to ensure that the start
        # of all the targets happens before StateManager calls
        # the completion hook that tries to apply configuration params
        # for targets that haven't been set up yet.

        return steps

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']


class HostContactAlert(AlertState):
    def message(self):
        return "Lost contact with host %s" % self.alert_item

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

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


class HostOfflineAlert(AlertState):
    """Alert should be raised when a Host is known to be down.

    When a corosync agent reports a peer is down in a cluster, the corresponding
    service will save a HostOfflineAlert.
    """

    def message(self):
        return "Host is offline %s" % self.alert_item

    class Meta:
        app_label = 'chroma_core'

    def begin_event(self):
        return AlertEvent(
            message_str = "Host is offline %s" % self.alert_item,
            host = self.alert_item,
            alert = self,
            severity = logging.WARNING)

    def end_event(self):
        return AlertEvent(
            message_str = "Host is back online %s" % self.alert_item,
            host = self.alert_item,
            alert = self,
            severity = logging.INFO)


class HostRebootEvent(Event):
    boot_time = models.DateTimeField()

    class Meta:
        app_label = 'chroma_core'

    @staticmethod
    def type_name():
        return "Autodetection"

    def message(self):
        return "%s restarted at %s" % (self.host, self.boot_time)


class LNetOfflineAlert(AlertState):
    def message(self):
        return "LNet offline on server %s" % self.alert_item

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

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
        ordering = ['id']

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
