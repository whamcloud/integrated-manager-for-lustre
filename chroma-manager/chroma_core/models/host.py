#
# INTEL CONFIDENTIAL
#
# Copyright 2013 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


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
from chroma_core.lib.job import DependOn, DependAll, Step
from chroma_core.models.utils import MeasuredEntity, DeletableDowncastableMetaclass, DeletableMetaclass
from chroma_help.help import help_text

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

    # Recursive relationship to keep track of corosync cluster peers
    ha_cluster_peers = models.ManyToManyField('self', null = True, blank = True, help_text = "List of peers in this host's HA cluster")

    # Profile of the server specifying some configured characteristics
    # FIXME: nullable to allow migration, but really shouldn't be
    server_profile = models.ForeignKey('ServerProfile', null=True, blank=True)

    needs_update = models.BooleanField(default=False,
                                       help_text="True if there are package updates available for this server")

    needs_fence_reconfiguration = models.BooleanField(default = False,
            help_text = "Indicates that the host's fencing configuration should be updated")

    # FIXME: HYD-1215: separate the LNET state [unloaded, down, up] from the host state [created, removed]
    states = ['undeployed', 'unconfigured', 'configured', 'lnet_unloaded', 'lnet_down', 'lnet_up', 'removed']
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
                                  help_text = "Integer number of bytes.  "
                                              "Can be null if this device "
                                              "was manually created, rather "
                                              "than detected.")

    label = models.CharField(max_length = 128)

    filesystem_type = models.CharField(max_length = 32, blank = True, null = True)

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


class ConfigurePacemakerStep(Step):
    idempotent = True

    def run(self, kwargs):
        host = kwargs['host']
        if not host.immutable_state:
            self.invoke_agent(host, "configure_pacemaker")


class ConfigureCorosyncStep(Step):
    idempotent = True

    def run(self, kwargs):
        host = kwargs['host']

        if not host.immutable_state:
            # Empty dict if no host-side config.
            config = self.invoke_agent(host, "host_corosync_config")
            self.invoke_agent(host, "configure_corosync", config)


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


class UnconfigurePacemakerStep(Step):
    idempotent = True

    def run(self, kwargs):
        host = kwargs['host']
        if not host.immutable_state:
            self.invoke_agent(host, "unconfigure_pacemaker")


class UnconfigureCorosyncStep(Step):
    idempotent = True

    def run(self, kwargs):
        host = kwargs['host']
        if not host.immutable_state:
            self.invoke_agent(host, "unconfigure_corosync")


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


class DeployStep(Step):
    def run(self, kwargs):
        from chroma_core.services.job_scheduler.agent_rpc import AgentSsh

        # TODO: before kicking this off, check if an existing agent install is present:
        # the decision to clear it out/reset it should be something explicit maybe
        # even requiring user permission

        rc, stdout, stderr = AgentSsh(kwargs['address']).ssh('curl -k %s/agent/setup/%s/ | python' %
                                                             (settings.SERVER_HTTP_URL, kwargs['token'].secret),
                                                             auth_args=kwargs['__auth_args'])

        if rc == 0:
            try:
                registration_result = json.loads(stdout)
            except ValueError:
                raise RuntimeError("Failed to register host %s: rc=%s\n'%s'\n'%s'" % (kwargs['address'], rc, stdout, stderr))

            return registration_result['host_id'], registration_result['command_id']
        else:
            raise RuntimeError("Failed to register host %s: rc=%s\n'%s'\n'%s'" % (kwargs['address'], rc, stdout, stderr))


class AwaitRebootStep(Step):
    def run(self, kwargs):
        from chroma_core.services.job_scheduler.agent_rpc import AgentRpc

        AgentRpc.await_restart(kwargs['host'].fqdn, kwargs['timeout'])


class DeployHostJob(StateChangeJob):
    state_transition = (ManagedHost, 'undeployed', 'unconfigured')
    stateful_object = 'managed_host'
    managed_host = models.ForeignKey(ManagedHost)
    state_verb = 'Deploy agent'
    auth_args = {}

    # Not cancellable because uses SSH rather than usual agent comms
    cancellable = False

    def __init__(self, *args, **kwargs):
        super(DeployHostJob, self).__init__(*args, **kwargs)

    def description(self):
        return "Deploying agent to %s" % self.managed_host.address

    def get_steps(self):
        from chroma_core.models.registration_token import RegistrationToken

        # Commit token so that registration request handler will see it
        with transaction.commit_on_success():
            token = RegistrationToken.objects.create(credits=1, profile=self.managed_host.server_profile)

        return [
            (DeployStep, {
                'token': token,
                'address': self.managed_host.address,
                '__auth_args': self.auth_args},)
        ]

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']


class RebootIfNeededStep(Step):
    def _reboot_needed(self, host):
        # Check if we are running the latest (lustre) kernel
        kernel_status = self.invoke_agent(host, 'kernel_status', {'kernel_regex': '.*lustre.*'})

        reboot_required = kernel_status['running'] != kernel_status['latest'] and kernel_status['latest']
        if reboot_required:
            self.log("Reboot of %s required to switch from running kernel %s to latest %s" % (
                host, kernel_status['running'], kernel_status['latest']))

        return reboot_required

    def run(self, kwargs):
        if self._reboot_needed(kwargs['host']):
            self.invoke_agent(kwargs['host'], 'reboot_server')

            from chroma_core.services.job_scheduler.agent_rpc import AgentRpc

            AgentRpc.await_restart(kwargs['host'].fqdn, kwargs['timeout'])


class InstallPackagesStep(Step):
    # Require database because we update package records
    database = True

    @classmethod
    def describe(cls, kwargs):
        return "Installing packages on %s" % kwargs['host']

    def run(self, kwargs):
        from chroma_core.models import package

        host = kwargs['host']
        packages = kwargs['packages']

        package_report = self.invoke_agent(host, 'install_packages', {
            'packages': packages,
            'force_dependencies': True
        })

        if package_report:
            updates_available = package.update(host, package_report)
            UpdatesAvailableAlert.notify(host, updates_available)


class SetupHostJob(StateChangeJob):
    state_transition = (ManagedHost, 'unconfigured', 'configured')
    stateful_object = 'managed_host'
    managed_host = models.ForeignKey(ManagedHost)
    state_verb = 'Set up server'

    def description(self):
        return "Set up server %s" % self.managed_host

    def get_steps(self):
        steps = [(ConfigureNTPStep, {'host': self.managed_host}),
                 (ConfigureRsyslogStep, {'host': self.managed_host}),
                 (LearnDevicesStep, {'host': self.managed_host})]

        if self.managed_host.server_profile.managed:
            steps.append((InstallPackagesStep, {
                'host': self.managed_host,
                'packages': list(self.managed_host.server_profile.packages)
            }))

            steps.append((RebootIfNeededStep, {'host': self.managed_host, 'timeout': settings.INSTALLATION_REBOOT_TIMEOUT}))

            steps.extend([
                (ConfigureCorosyncStep, {'host': self.managed_host}),
                (ConfigurePacemakerStep, {'host': self.managed_host})
            ])

        return steps

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
    long_description = help_text["start_lnet"]

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
    long_description = help_text["unload_lnet"]

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
    long_description = help_text["start_lnet"]

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
    long_description = help_text["stop_lnet"]

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
        from chroma_core.models import package
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

        # Remove PackageAvailability and PackageInstallation records for this host
        package.update(host, {})

        from chroma_core.models import StorageResourceRecord
        from chroma_core.services.plugin_runner.agent_daemon_interface import AgentDaemonRpcInterface
        try:
            AgentDaemonRpcInterface().remove_host_resources(host.id)
        except StorageResourceRecord.DoesNotExist:
            # This is allowed, to account for the case where we submit the request_remove_resource,
            # then crash, then get restarted.
            pass

        # Remove associations with PDU outlets
        for outlet in host.outlets.all():
            if kwargs['force']:
                outlet.force_host_disassociation()
            else:
                outlet.host = None
                outlet.save()

        host.mark_deleted()
        if kwargs['force']:
            host.state = 'removed'


class RemoveHostJob(StateChangeJob):
    state_transition = (ManagedHost, ['unconfigured', 'configured', 'lnet_up', 'lnet_down', 'lnet_unloaded'], 'removed')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)
    state_verb = 'Remove'
    long_description = help_text['remove_server']

    requires_confirmation = True

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    def description(self):
        return "Remove host %s from configuration" % self.host

    def get_steps(self):
        return [(UnconfigureNTPStep, {'host': self.host}),
                (UnconfigurePacemakerStep, {'host': self.host}),
                (UnconfigureCorosyncStep, {'host': self.host}),
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

    long_description = help_text['force_remove']

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

    @classmethod
    def can_run(cls, host):
        return (host.state not in ['removed', 'undeployed', 'unconfigured'] and
                not AlertState.filter_by_item(host).filter(
                        active = True,
                        alert_type__in = [
                            HostOfflineAlert.__name__,
                            HostContactAlert.__name__
                        ]
                    ).exists()
                )

    def description(self):
        return "Initiate a reboot on host %s" % self.host

    def get_steps(self):
        return [
            (RebootHostStep, {'host': self.host})
        ]

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

    @classmethod
    def can_run(cls, host):
        return (host.state not in ['removed', 'undeployed', 'unconfigured'] and
                not AlertState.filter_by_item(host).filter(
                        active = True,
                        alert_type__in = [
                            HostOfflineAlert.__name__,
                            HostContactAlert.__name__
                        ]
                    ).exists()
                )

    def description(self):
        return "Initiate an orderly shutdown on host %s" % self.host

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


class UpdatePackagesStep(RebootIfNeededStep):
    # Require database because we update package records
    database = True

    def run(self, kwargs):
        from chroma_core.models import package
        from chroma_core.services.job_scheduler.agent_rpc import AgentRpc

        host = kwargs['host']
        package_report = self.invoke_agent(host, 'update_packages', {
            'repos': kwargs['bundles'],
            'packages': kwargs['packages']
        })

        if package_report:
            package.update(host, package_report)

        # Check if we are running the latest (lustre) kernel
        kernel_status = self.invoke_agent(kwargs['host'], 'kernel_status', {'kernel_regex': '.*lustre.*'})
        reboot_needed = kernel_status['running'] != kernel_status['latest'] and kernel_status['latest']

        if reboot_needed:
            # If the kernel has been upgraded, then we must reboot the server
            old_session_id = AgentRpc.get_session_id(host.fqdn)
            self.invoke_agent(kwargs['host'], 'reboot_server')
            AgentRpc.await_restart(kwargs['host'].fqdn, settings.INSTALLATION_REBOOT_TIMEOUT, old_session_id=old_session_id)
        elif package_report is not None:
            # If we have installed any updates at all, then assume it is necessary to restart the agent, as
            # they could be things the agent uses/imports
            old_session_id = AgentRpc.get_session_id(host.fqdn)
            self.invoke_agent(host, 'restart_agent')
            AgentRpc.await_restart(kwargs['host'].fqdn, timeout=settings.AGENT_RESTART_TIMEOUT, old_session_id=old_session_id)
        else:
            self.log("No updates installed on %s" % host)


class UpdateJob(Job):
    host = models.ForeignKey(ManagedHost)

    def description(self):
        return "Update packages on server %s" % self.host

    def get_steps(self):
        return [
            (UpdatePackagesStep, {
                'host': self.host,
                'bundles': [b['bundle_name'] for b in self.host.server_profile.bundles.all().values('bundle_name')],
                'packages': list(self.host.server_profile.packages)
            })
        ]

    def on_success(self):
        from chroma_core.models.host import UpdatesAvailableAlert

        UpdatesAvailableAlert.notify(self.host, False)

    class Meta:
        app_label = 'chroma_core'


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
    # This is worse than INFO because it *could* indicate that
    # a filesystem is unavailable, but it is not necessarily
    # so:
    # * Host can lose contact with us but still be servicing clients
    # * Host can be offline entirely but filesystem remains available
    #   if failover servers are available.
    default_severity = logging.WARNING

    def message(self):
        return "Lost contact with host %s" % self.alert_item

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

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

    # This is worse than INFO because it *could* indicate that
    # a filesystem is unavailable, but it is not necessarily
    # so:
    # * Host can be offline but filesystem remains available
    #   if failover servers are available.
    default_severity = logging.WARNING

    def message(self):
        return "Host is offline %s" % self.alert_item

    class Meta:
        app_label = 'chroma_core'

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
    # LNET being offline is never solely responsible for a filesystem
    # being unavailable: if a target is offline we will get a separate
    # ERROR alert for that.  LNET being offline may indicate a configuration
    # fault, but equally could just indicate that the host hasn't booted up that far yet.
    default_severity = logging.INFO

    def message(self):
        return "LNet offline on server %s" % self.alert_item

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    def end_event(self):
        return AlertEvent(
            message_str = "LNet started on server '%s'" % self.alert_item,
            host = self.alert_item,
            alert = self,
            severity = logging.INFO)


class LNetNidsChangedAlert(AlertState):
    # This is WARNING because targets on this host will not work
    # correctly until it is addressed, but the filesystem may still
    # be available if a failover server is not in this conditon.
    default_severity = logging.WARNING

    def message(self):
        return "NIDs changed on server %s" % self.alert_item

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    def end_event(self):
        return AlertEvent(
            message_str = "LNet NIDs updated for server %s" % self.alert_item,
            host = self.alert_item,
            alert = self,
            severity = logging.INFO)


class UpdatesAvailableAlert(AlertState):
    # This is INFO because the system is unlikely to be suffering as a consequence
    # of having an older software version installed.
    default_severity = logging.INFO

    def message(self):
        return "Updates are ready for server %s" % self.alert_item

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']


class NoLNetInfo(Exception):
    pass
