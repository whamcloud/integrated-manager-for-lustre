# -*- coding: utf-8 -*-
#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2014 Intel Corporation All Rights Reserved.
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
import re
import logging
import itertools

from django.db import models
from django.db import transaction
from django.db import IntegrityError

from django.db.models.aggregates import Aggregate, Count
from django.db.models.sql import aggregates as sql_aggregates
from django.core.exceptions import ObjectDoesNotExist
from collections import namedtuple

from django.db.models.query_utils import Q

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
        ordering = ['id']


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

    client_filesystems = models.ManyToManyField('ManagedFilesystem', related_name="workers", through="LustreClientMount", help_text="Filesystems for which this node is a non-server worker")

    # The fields below are how the agent was installed or how it was attempted to install in the case of a failed install
    INSTALL_MANUAL = 'manual'                          # The agent was installed manually by the user logging into the server and running a command
    INSTALL_SSHPSW = 'id_password_root'                # The user provided a password for the server so that ssh could be used for agent install
    INSTALL_SSHPKY = 'private_key_choice'              # The user provided a private key with password the agent install
    INSTALL_SSHSKY = 'existing_keys_choice'            # The server can be contacted via a shared key for the agent install

    # The method used to install the host
    install_method = models.CharField(max_length = 32, help_text = "The method used to install the agent on the server")

    # FIXME: HYD-1215: separate the LNET state [unloaded, down, up] from the host state [created, removed]
    states = ['unconfigured', 'undeployed', 'configured', 'lnet_unloaded', 'lnet_down', 'lnet_up', 'removed']
    initial_state = 'unconfigured'

    class Meta:
        app_label = 'chroma_core'
        unique_together = ('address',)
        ordering = ['id']

    def __str__(self):
        return self.get_label()

    @property
    def is_worker(self):
        return self.server_profile.worker

    @property
    def is_lustre_server(self):
        return not self.server_profile.worker

    @property
    def is_managed(self):
        return self.server_profile.managed

    @property
    def is_monitor_only(self):
        return not self.server_profile.managed

    @property
    def member_of_available_filesystem(self):
        """Return True if any part of this host or its FK dependents are related to an available filesystem

        See usage in chroma_apy/host.py:  used to determine if safe to configure LNet.
        """

        # To prevent circular imports
        from chroma_core.models.filesystem import ManagedFilesystem

        # Host is part of an available filesystem.
        for filesystem in ManagedFilesystem.objects.filter(state = 'available'):
            if self in filesystem.get_servers():
                return True

        # Host has any associated copytools related to an available filesystem.
        if self.copytools.filter(filesystem__state='available').exists():
            return True

        # This host is not related to any available filesystems.
        return False

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
        if begin_state == 'undeployed':
            return ['configured'] if self.install_method != ManagedHost.INSTALL_MANUAL else []

        if self.immutable_state:
            if begin_state in ['undeployed', 'unconfigured']:
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

        # Check we at least have a @
        if not "@" in nid_string:
            raise ManagedHost.DoesNotExist()

        nid = Nid.split_nid_string(nid_string)

        hosts = ManagedHost._base_manager.filter(networkinterface__inet4_address = nid.nid_address,
                                                 networkinterface__type = nid.lnd_type,
                                                 not_deleted = True)
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
            LNetOfflineAlert.notify_warning(self, self.state != 'lnet_up')
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


class LNetConfiguration(models.Model):

    # Chris: This will move to a stateful object at some point
    #StatefulObject):
    #states = ['nids_unknown', 'nids_known']
    #initial_state = 'nids_unknown'

    host = models.OneToOneField('ManagedHost')

    # Valid states are 'lnet_up', 'lnet_down', 'lnet_unloaded'. As we fully implement dynamic lnet these object
    # may go back to being a StatefulObject but we need to do this one step at a time. So for now we just do it
    # like this.
    state = models.CharField(max_length = 16, help_text = "The current state of the lnet configuration")

    def get_nids(self):
        return [n.nid_string for n in self.nid_set.all()]

    def __str__(self):
        return "%s LNet configuration" % (self.host)

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']


class NetworkInterface(models.Model):
    host = models.ForeignKey('ManagedHost')

    name = models.CharField(max_length=32)
    inet4_address = models.CharField(max_length=128)
    type = models.CharField(max_length=32)          # tcp, o2ib, ... (best stick to lnet types!)
    state_up = models.BooleanField()

    def __str__(self):
        return "%s-%s" % (self.host, self.name)

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']
        unique_together = ('host', 'name')


class Nid(models.Model):
    """Simplified NID representation for those we detect already-configured"""
    lnet_configuration = models.ForeignKey(LNetConfiguration)
    network_interface = models.OneToOneField(NetworkInterface, primary_key = True)

    lnd_network = models.IntegerField(null=True)

    @property
    def nid_string(self):
        return ("%s@%s%s" % (self.network_interface.inet4_address,
                             self.network_interface.type,
                             self.lnd_network))

    @property
    def modprobe_entry(self):
        return("%s%s(%s)" % (self.network_interface.type,
                             self.lnd_network,
                             self.network_interface.name))

    @property
    def to_tuple(self):
        return tuple([self.network_interface.inet4_address,
                      self.network_interface.type,
                      self.lnd_network])

    @classmethod
    def nid_tuple_to_string(cls, nid):
        return ("%s@%s%s" % (nid.nid_address,
                             nid.lnd_type,
                             nid.lnd_network))

    Nid = namedtuple("Nid", ["nid_address", "lnd_type", "lnd_network"])

    @classmethod
    def split_nid_string(cls, nid_string):
        '''
        :param nid_string: Can be multiple format tcp0, tcp, tcp1234, o2ib0, o2ib (not number in the word)
        :return: Nid name tuple containing the address, the lnd_type or the lnd_network
        '''
        assert '@' in nid_string, "Malformed NID?!: %s"

        # Split the nid so we can search correctly on its parts.
        nid_address = nid_string.split("@")[0]
        type_network_no = nid_string.split("@")[1]
        m = re.match('(\w+?)(\d+)?$', type_network_no)   # Non word, then optional greedy number at end of line.
        lnd_type = m.group(1)
        lnd_network = m.group(2)
        if not lnd_network:
            lnd_network = 0

        return Nid.Nid(nid_address, lnd_type, lnd_network)

    class Meta:
        app_label = 'chroma_core'
        ordering = ['network_interface']


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
        from chroma_core.services.job_scheduler.agent_rpc import AgentException

        host = kwargs['host']

        try:
            lnet_data = self.invoke_agent(host, "device_plugin", {'plugin': 'linux_network'})['linux_network']['lnet']
            host.set_state(lnet_data['state'])
            host.save()
        except TypeError:
            self.log("Data received from old client. Host %s state cannot be updated until agent is updated" % host)
        except AgentException as e:
            self.log("No data for plugin linux_network from host %s due to exception %s" % (host, e))


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
            write = True
        )]

    @classmethod
    def get_args(cls, host):
        return {'host': host}

    @classmethod
    def long_description(cls, stateful_object):
        return help_text['lnet_state']

    def description(self):
        return "Get LNet state for %s" % self.host

    def get_steps(self):
        return [(GetLNetStateStep, {'host': self.host})]

    def get_deps(self):
        # This is another piece of  HYD-1215 and test stuff, this just forces the lnet to be loaded if this is
        # the first time this is called - the configured state doesn't really exist it is really lnet_unloaded.
        # Of course if the host is not managed we can't depend on it's state - because the would change it's state.
        if self.host.is_managed and self.host.state == 'configured':
            return DependOn(self.host, 'lnet_up')
        else:
            return super(GetLNetStateJob, self).get_deps()


class ConfigureLNetStep(Step):
    idempotent = True

    # FIXME: using database=True to do the alerting update inside .set_state but
    # should do it in a completion
    database = True

    def run(self, kwargs):
        host = kwargs['host']
        nid_updates = kwargs['config_changes']['nid_updates']
        nid_deletes = kwargs['config_changes']['nid_deletes']

        modprobe_entries = []
        nid_tuples = []

        network_interfaces = NetworkInterface.objects.filter(host=host)
        lnet_configuration = LNetConfiguration.objects.get(host=host)

        for network_interface in network_interfaces:
            # See if we have deleted the nid for this network interface or
            # see if we have a new configuration for this if we do then it
            # will replace the current configuration.
            #
            # The int will have become a string - we should use a PickledObjectField really.
            if str(network_interface.id) in nid_deletes:
                nid = None
            elif str(network_interface.id) in nid_updates:
                nid = Nid(network_interface = network_interface,
                          lnet_configuration = lnet_configuration,
                          lnd_network = nid_updates[str(network_interface.id)]['lnd_network'])
            else:
                try:
                    nid = Nid.objects.get(network_interface = network_interface)
                except ObjectDoesNotExist:
                    nid = None
                    pass

            if nid is not None:
                modprobe_entries.append(nid.modprobe_entry)
                nid_tuples.append(nid.to_tuple)

        self.invoke_agent(host,
                          "configure_lnet",
                          {'lnet_configuration': {'state': lnet_configuration.state,
                                                  'modprobe_entries': modprobe_entries,
                                                  'network_interfaces': nid_tuples}})


class UnconfigureLNetStep(Step):
    idempotent = True

    def run(self, kwargs):
        host = kwargs['host']
        if not host.immutable_state:
            self.invoke_agent(host, "unconfigure_lnet")


class ConfigureLNetJob(Job):
    host = models.ForeignKey(ManagedHost)
    config_changes = models.CharField(max_length = 4096, help_text = "A json string describing the configuration changes")
    requires_confirmation = False
    state_verb = "Configure LNet"

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    def create_locks(self):
        return [StateLock(
            job = self,
            locked_item = self.host,
            write = True
        )]

    @classmethod
    def get_args(cls, host):
        return {'host': host}

    @classmethod
    def long_description(cls, stateful_object):
        return help_text['configure_lnet']

    def description(self):
        return "Configure LNet for %s" % self.host

    def get_steps(self):
        # The get_deps means the lnet is always placed into the unloaded state in preparation for the change in
        # configure the next two steps cause lnet to return to the state it was in
        steps = [(ConfigureLNetStep, {'host': self.host, 'config_changes': json.loads(self.config_changes)})]

        if (self.host.state != 'lnet_unloaded'):
            steps.append((LoadLNetStep, {'host': self.host}))

        if (self.host.state == 'lnet_up'):
            steps.append((StartLNetStep, {'host': self.host}))

        steps.append((UpdateDevicesStep, {'host': self.host}))

        return steps

    def get_deps(self):
        return DependOn(self.host, 'lnet_unloaded')


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


class UpdateDevicesStep(Step):
    idempotent = True

    # Require database to talk to plugin_manager
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
                plugin_data[plugin] = self.invoke_agent(host, 'device_plugin', {'plugin': plugin})[plugin]
            except AgentException as e:
                self.log("No data for plugin %s from host %s due to exception %s" % (plugin, host, e))

        # This enables services tests to run see - _handle_action_respond in test_agent_rpc.py for more info
        if (plugin_data != {}):
            AgentDaemonRpcInterface().update_host_resources(host.id, plugin_data)
        else:
            pass


class DeployStep(Step):
    def run(self, kwargs):
        from chroma_core.services.job_scheduler.agent_rpc import AgentSsh

        # TODO: before kicking this off, check if an existing agent install is present:
        # the decision to clear it out/reset it should be something explicit maybe
        # even requiring user permission
        agent_ssh = AgentSsh(kwargs['address'])
        auth_args = agent_ssh.construct_ssh_auth_args(kwargs['__auth_args']['root_pw'],
                                                      kwargs['__auth_args']['pkey'],
                                                      kwargs['__auth_args']['pkey_pw'])

        rc, stdout, stderr = agent_ssh.ssh('curl -k %s/agent/setup/%s/%s | python' %
                                                             (settings.SERVER_HTTP_URL,
                                                              kwargs['token'].secret,
                                                              '?profile_name=%s' % kwargs['profile_name']),
                                                              auth_args=auth_args)

        if rc == 0:
            try:
                registration_result = json.loads(stdout)
            except ValueError:
                # Not valid JSON
                raise RuntimeError("Failed to register host %s: rc=%s\n'%s'\n'%s'" % (kwargs['address'], rc, stdout, stderr))

            return registration_result['host_id'], registration_result['command_id']
        else:
            raise RuntimeError("Failed to register host %s: rc=%s\n'%s'\n'%s'" % (kwargs['address'], rc, stdout, stderr))


class AwaitRebootStep(Step):
    def run(self, kwargs):
        from chroma_core.services.job_scheduler.agent_rpc import AgentRpc

        AgentRpc.await_restart(kwargs['host'].fqdn, kwargs['timeout'])


class DeployHostJob(StateChangeJob):
    """Handles Deployment of the IML agent code base to a new host"""

    state_transition = (ManagedHost, 'undeployed', 'unconfigured')
    stateful_object = 'managed_host'
    managed_host = models.ForeignKey(ManagedHost)
    state_verb = 'Deploy agent'
    auth_args = {}

    # Not cancellable because uses SSH rather than usual agent comms
    cancellable = False

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 10

    def __init__(self, *args, **kwargs):
        super(DeployHostJob, self).__init__(*args, **kwargs)

    @classmethod
    def long_description(cls, stateful_object):
        return help_text['deploy_agent']

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
                'profile_name': self.managed_host.server_profile.name,
                '__auth_args': self.auth_args},)
        ]

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']


class RebootIfNeededStep(Step):
    def _reboot_needed(self, host):
        # Check if we are running the required (lustre) kernel
        kernel_status = self.invoke_agent(host, 'kernel_status')

        reboot_needed = (kernel_status['running'] != kernel_status['required']
                         and kernel_status['required']
                         and kernel_status['required'] in kernel_status['available'])
        if reboot_needed:
            self.log("Reboot of %s required to switch from running kernel %s to required %s" % (
                host, kernel_status['running'], kernel_status['required']))

        return reboot_needed

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
    state_verb = 'Setup server'

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 20

    @classmethod
    def long_description(cls, stateful_object):
        return help_text['setup_host']

    def description(self):
        return "Setup server %s" % self.managed_host

    def get_steps(self):
        steps = [(ConfigureNTPStep, {'host': self.managed_host}),
                 (ConfigureRsyslogStep, {'host': self.managed_host})]

        if self.managed_host.is_lustre_server:
            steps.append((LearnDevicesStep, {'host': self.managed_host}))

        if not self.managed_host.is_monitor_only:
            steps.append((InstallPackagesStep, {
                'host': self.managed_host,
                'packages': list(self.managed_host.server_profile.packages)
            }))

            steps.append((RebootIfNeededStep, {
                'host': self.managed_host,
                'timeout': settings.INSTALLATION_REBOOT_TIMEOUT
            }))

            if self.managed_host.is_lustre_server:
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

    @classmethod
    def long_description(cls, stateful_object):
        return help_text['enable_lnet']

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

    @classmethod
    def long_description(cls, stateful_object):
        return help_text['detect_targets']

    def description(self):
        return "Scan for Lustre targets"

    def get_steps(self):
        return [(DetectTargetsStep, {'host_ids': [h.id for h in self.hosts.all()]})]

    def get_deps(self):
        deps = []
        for host in self.hosts.all():
            deps.append(DependOn(host, 'lnet_up'))

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

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 30

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["start_lnet"]

    def description(self):
        return "Load LNet module on %s" % self.host

    def get_steps(self):
        return [(LoadLNetStep, {'host': self.host}),
                (UpdateDevicesStep, {'host': self.host})]


class UpdateDevicesJob(Job, HostListMixin):
    @classmethod
    def long_description(cls, stateful_object):
        return help_text['update_devices']

    def description(self):
        return "Update the device info held for hosts %s" % ",".join([h.fqdn for h in self.hosts.all()])

    def get_deps(self):
        deps = []
        for host in self.hosts.all():
            deps.append(DependOn(host, "lnet_up"))
        return DependAll(deps)

    def get_steps(self):
        return [(UpdateDevicesStep, {'host': host})
                for host in self.hosts.all()]

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']


class UnloadLNetJob(StateChangeJob):
    state_transition = (ManagedHost, 'lnet_down', 'lnet_unloaded')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)
    state_verb = 'Unload LNet'

    display_group = Job.JOB_GROUPS.RARE
    display_order = 110

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["unload_lnet"]

    def description(self):
        return "Unload LNet module on %s" % self.host

    def get_steps(self):
        return [(UnloadLNetStep, {'host': self.host}),
                (UpdateDevicesStep, {'host': self.host})]


class StartLNetJob(StateChangeJob):
    state_transition = (ManagedHost, 'lnet_down', 'lnet_up')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)
    state_verb = 'Start LNet'

    display_group = Job.JOB_GROUPS.COMMON
    display_order = 40

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["start_lnet"]

    def description(self):
        return "Start LNet on %s" % self.host

    def get_steps(self):
        return [(StartLNetStep, {'host': self.host}),
                (UpdateDevicesStep, {'host': self.host})]


class StopLNetJob(StateChangeJob):
    state_transition = (ManagedHost, 'lnet_up', 'lnet_down')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)
    state_verb = 'Stop LNet'

    display_group = Job.JOB_GROUPS.RARE
    display_order = 100

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["stop_lnet"]

    def description(self):
        return "Stop LNet on %s" % self.host

    def get_steps(self):
        return [(StopLNetStep, {'host': self.host}),
                (UpdateDevicesStep, {'host': self.host})]


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

        # Remove associations with PDU outlets, or delete IPMI BMCs
        for outlet in host.outlets.select_related():
            if outlet.device.is_ipmi:
                outlet.mark_deleted()
        host.outlets.update(host=None)

        # Remove associated lustre mounts
        for mount in host.client_mounts.all():
            mount.mark_deleted()

        host.mark_deleted()
        if kwargs['force']:
            host.state = 'removed'


class RemoveHostJob(StateChangeJob):
    state_transition = (ManagedHost, ['unconfigured', 'configured', 'lnet_up', 'lnet_down', 'lnet_unloaded'], 'removed')
    stateful_object = 'host'
    host = models.ForeignKey(ManagedHost)
    state_verb = 'Remove'

    requires_confirmation = True

    display_group = Job.JOB_GROUPS.EMERGENCY
    display_order = 120

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    @classmethod
    def long_description(cls, stateful_object):
        if stateful_object.immutable_state:
            return help_text['remove_monitored_configured_server']
        else:
            return help_text['remove_configured_server']

    def get_confirmation_string(self):
        return RemoveHostJob.long_description(self.host)

    def description(self):
        return "Remove host %s from configuration" % self.host

    def get_steps(self):
        steps = [(UnconfigureNTPStep, {'host': self.host})]

        if self.host.is_lustre_server:
            steps.extend([
                (UnconfigurePacemakerStep, {'host': self.host}),
                (UnconfigureCorosyncStep, {'host': self.host})
            ])

        steps.extend([
            (UnconfigureRsyslogStep, {'host': self.host}),
            (UnconfigureLNetStep, {'host': self.host}),
            (RemoveServerConfStep, {'host': self.host}),
            (DeleteHostStep, {'host': self.host, 'force': False})
        ])

        return steps


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
    mounts = set(list(host.client_mounts.distinct()))
    copytools = set(list(host.copytools.distinct()))

    return targets, filesystems, mounts, copytools


class DeleteHostDependents(Step):
    idempotent = True
    database = True

    def run(self, kwargs):
        host = kwargs['host']
        targets, filesystems, mounts, copytools = _get_host_dependents(host)

        job_log.info("DeleteHostDependents(%s): targets: %s, filesystems: %s, client_mounts: %s, copytools: %s" % (host, targets, filesystems, mounts, copytools))

        # This keeps the UI sane... Faster than waiting around for an
        # expiration.
        for copytool in copytools:
            copytool.cancel_current_operations()

        for object in itertools.chain(targets, filesystems, mounts, copytools):
            # We are allowed to modify state directly because we have locked these objects
            object.set_state('removed')
            object.mark_deleted()
            object.save()


class ForceRemoveHostJob(AdvertisedJob):
    host = models.ForeignKey(ManagedHost)

    requires_confirmation = True

    classes = ['ManagedHost']

    verb = "Force Remove"

    display_group = Job.JOB_GROUPS.LAST_RESORT
    display_order = 140

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    @classmethod
    def long_description(cls, stateful_object):
        return help_text['force_remove']

    def create_locks(self):
        locks = super(ForceRemoveHostJob, self).create_locks()

        locks.append(StateLock(
            job = self,
            locked_item = self.host,
            begin_state = None,
            end_state = 'removed',
            write = True
        ))

        targets, filesystems, mounts, copytools = _get_host_dependents(self.host)
        # Take a write lock on get_stateful_object if this is a StateChangeJob
        for object in itertools.chain(targets, filesystems, mounts, copytools):
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
        return """WARNING This command is destructive. This command should only be performed
when the Remove command has been unsuccessful. This command will remove this server from the
Intel® Manager for Lustre configuration, but Intel® Manager for Lustre software will not be removed
from this server.  All targets that depend on this server will also be removed without any attempt to
unconfigure them. To completely remove the Intel® Manager for Lustre software from this server
(allowing it to be added to another Lustre file system) you must first contact technical support.
You should only perform this command if this server is permanently unavailable, or has never been
successfully deployed using Intel® Manager for Lustre software."""


class RebootHostJob(AdvertisedJob):
    host = models.ForeignKey(ManagedHost)

    requires_confirmation = True

    classes = ['ManagedHost']

    verb = "Reboot"

    display_group = Job.JOB_GROUPS.INFREQUENT
    display_order = 50

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    @classmethod
    def long_description(cls, stateful_object):
        return help_text['reboot_host']

    @classmethod
    def get_args(cls, host):
        return {'host_id': host.id}

    @classmethod
    def can_run(cls, host):
        if host.immutable_state:
            return False

        return (host.state not in ['removed', 'undeployed', 'unconfigured'] and
                not AlertState.filter_by_item(host).filter(
                    active = True,
                    alert_type__in = [
                        HostOfflineAlert.__name__,
                        HostContactAlert.__name__
                    ]
                ).exists())

    def description(self):
        return "Initiate a reboot on host %s" % self.host

    def get_steps(self):
        return [
            (RebootHostStep, {'host': self.host})
        ]

    @classmethod
    def get_confirmation(cls, stateful_object):
        cls.long_description(stateful_object)


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

    display_group = Job.JOB_GROUPS.INFREQUENT
    display_order = 60

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    @classmethod
    def long_description(cls, stateful_object):
        return help_text['shutdown_host']

    @classmethod
    def get_args(cls, host):
        return {'host_id': host.id}

    @classmethod
    def can_run(cls, host):
        if host.immutable_state:
            return False

        return (host.state not in ['removed', 'undeployed', 'unconfigured'] and
                not AlertState.filter_by_item(host).filter(
                    active = True,
                    alert_type__in = [
                        HostOfflineAlert.__name__,
                        HostContactAlert.__name__
                    ]
                ).exists())

    def description(self):
        return "Initiate an orderly shutdown on host %s" % self.host

    def get_steps(self):
        return [(ShutdownHostStep, {'host': self.host})]

    @classmethod
    def get_confirmation(cls, stateful_object):
        return cls.long_description(stateful_object)


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

    requires_confirmation = True

    display_group = Job.JOB_GROUPS.EMERGENCY
    display_order = 130

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    @classmethod
    def long_description(cls, stateful_object):
        return help_text['remove_unconfigured_server']

    def get_confirmation_string(self):
        return RemoveUnconfiguredHostJob.long_description(None)

    def description(self):
        return "Remove host %s from configuration" % self.host

    def get_steps(self):
        return [(DeleteHostStep, {'host': self.host, 'force': False})]


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

            # If we have installed any updates at all, then assume it is necessary to restart the agent, as
            # they could be things the agent uses/imports or API changes, specifically to kernel_status() below
            old_session_id = AgentRpc.get_session_id(host.fqdn)
            self.invoke_agent(host, 'restart_agent')
            AgentRpc.await_restart(kwargs['host'].fqdn, timeout=settings.AGENT_RESTART_TIMEOUT, old_session_id=old_session_id)
        else:
            self.log("No updates installed on %s" % host)

        # Now do some managed things
        if host.is_managed:
            # Upgrade of pacemaker packages could have left it disabled
            self.invoke_agent(kwargs['host'], 'enable_pacemaker')

            # Check if we are running the required (lustre) kernel
            kernel_status = self.invoke_agent(kwargs['host'], 'kernel_status')
            reboot_needed = (kernel_status['running'] != kernel_status['required']
                             and kernel_status['required']
                             and kernel_status['required'] in kernel_status['available'])

            if reboot_needed:
                # If the required kernel has been upgraded, then we must reboot the server
                old_session_id = AgentRpc.get_session_id(host.fqdn)
                self.invoke_agent(kwargs['host'], 'reboot_server')
                AgentRpc.await_restart(kwargs['host'].fqdn, settings.INSTALLATION_REBOOT_TIMEOUT, old_session_id=old_session_id)


class UpdateJob(Job):
    host = models.ForeignKey(ManagedHost)

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["update_packages"]

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
            'erase_params': True,
            'device': args['path']}

        if issubclass(target.downcast_class, FilesystemMember):
            agent_args['mgsnode'] = args['mgsnode']
            agent_args['writeconf'] = True

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
    @classmethod
    def long_description(cls, stateful_object):
        return help_text["update_nids"]

    def description(self):
        if self.hosts.count() > 1:
            return "Update NIDs on %d hosts" % self.hosts.count()
        else:
            return "Update NIDs on host %s" % self.hosts.all()[0]

    def _targets_on_hosts(self):
        from chroma_core.models.target import ManagedMgs, ManagedTarget, FilesystemMember
        from chroma_core.models.filesystem import ManagedFilesystem

        filesystems = set()
        targets = set()
        for target in ManagedTarget.objects.filter(managedtargetmount__host__in = self.hosts.all()):
            targets.add(target)
            if issubclass(target.downcast_class, FilesystemMember):
                # FIXME: N downcasts :-(
                filesystems.add(target.downcast().filesystem)

            if issubclass(target.downcast_class, ManagedMgs):
                for fs in target.downcast().managedfilesystem_set.all():
                    filesystems.add(fs)

        for fs in filesystems:
            targets |= set(fs.get_targets())

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

        steps = []
        for target in targets:
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
    # be available if a failover server is not in this condition.
    default_severity = logging.WARNING

    def message(self):
        msg = "NIDs changed on server %s - see manual for details."
        return msg % self.alert_item

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


class NoNidsPresent(Exception):
    pass
