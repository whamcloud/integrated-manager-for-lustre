# -*- coding: utf-8 -*-
#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2015 Intel Corporation All Rights Reserved.
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

from django.db import models
from django.db import transaction
from django.db import IntegrityError
from django.utils.timezone import now as tznow

from django.db.models.aggregates import Aggregate, Count
from django.db.models.sql import aggregates as sql_aggregates

from django.db.models.query_utils import Q

from chroma_core.lib.cache import ObjectCache
from chroma_core.models import StateChangeJob, DeletableStatefulObject
from chroma_core.models import NullStateChangeJob
from chroma_core.models import Event
from chroma_core.models import AlertState
from chroma_core.models import AlertEvent
from chroma_core.models import ServerProfile
from chroma_core.models import PacemakerConfiguration
from chroma_core.models import CorosyncConfiguration
from chroma_core.models import NTPConfiguration
from chroma_core.models import RSyslogConfiguration
from chroma_core.models import Job, AdvertisedJob, StateLock
from chroma_core.lib.job import job_log
from chroma_core.lib.job import DependOn, DependAll, DependAny, Step
from chroma_core.models.utils import MeasuredEntity, DeletableMetaclass
from chroma_help.help import help_text
from chroma_core.services.job_scheduler import job_scheduler_notify

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
class HostListMixin(Job):
    class Meta:
        abstract = True
        app_label = 'chroma_core'

    host_ids = models.CharField(max_length = 512)

    def __init__(self, *args, **kwargs):
        self._cached_host_ids = "None-Cached"
        super(HostListMixin, self).__init__(*args, **kwargs)

    @property
    def hosts(self):
        if self._cached_host_ids != self.host_ids:
            if not self.host_ids:
                hosts = ManagedHost.objects.all()
            else:
                hosts = ManagedHost.objects.filter(id__in = json.loads(self.host_ids))

            self._hosts = list(hosts)
            self._cached_host_ids = self.host_ids

        return self._hosts


class ManagedHost(DeletableStatefulObject, MeasuredEntity):
    address = models.CharField(max_length = 255, help_text = "A URI like 'user@myhost.net:22'")

    # A fully qualified domain name like flint02.testnet
    fqdn = models.CharField(max_length = 255, help_text = "Unicode string, fully qualified domain name")

    # a nodename to match against fqdn in corosync output
    nodename = models.CharField(max_length = 255, help_text = "Unicode string, node name")

    # The last known boot time
    boot_time = models.DateTimeField(null = True, blank = True)

    # Recursive relationship to keep track of cluster peers
    ha_cluster_peers = models.ManyToManyField('self', null = True, blank = True, help_text = "List of peers in this host's HA cluster")

    # Profile of the server specifying some configured characteristics
    # FIXME: nullable to allow migration, but really shouldn't be
    server_profile = models.ForeignKey('ServerProfile', null=True, blank=True)

    needs_update = models.BooleanField(default=False,
                                       help_text="True if there are package updates available for this server")

    client_filesystems = models.ManyToManyField('ManagedFilesystem', related_name="workers", through="LustreClientMount", help_text="Filesystems for which this node is a non-server worker")

    # The fields below are how the agent was installed or how it was attempted to install in the case of a failed install
    INSTALL_MANUAL = 'manual'                          # The agent was installed manually by the user logging into the server and running a command
    INSTALL_SSHPSW = 'id_password_root'                # The user provided a password for the server so that ssh could be used for agent install
    INSTALL_SSHPKY = 'private_key_choice'              # The user provided a private key with password the agent install
    INSTALL_SSHSKY = 'existing_keys_choice'            # The server can be contacted via a shared key for the agent install

    # The method used to install the host
    install_method = models.CharField(max_length = 32, help_text = "The method used to install the agent on the server")

    # JSON object of properties suitable for validation
    properties = models.TextField(default='{}')

    states = ['undeployed', 'unconfigured', 'packages_installed', 'managed', 'monitored', 'working', 'removed']
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
    def is_monitored(self):
        return not self.server_profile.managed

    @property
    def member_of_active_filesystem(self):
        """Return True if any part of this host or its FK dependents are related to an available filesystem

        See usage in chroma_apy/host.py:  used to determine if safe to configure LNet.
        """

        # To prevent circular imports
        from chroma_core.models.filesystem import ManagedFilesystem

        # Host is part of an available filesystem.
        for filesystem in ManagedFilesystem.objects.filter(state__in = ['available', 'unavailable']):
            if self in filesystem.get_servers():
                return True

        # Host has any associated copytools related to an available filesystem.
        if self.copytools.filter(filesystem__state__in = ['available', 'unavailable']).exists():
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
            return [self.server_profile.initial_state] if self.install_method != ManagedHost.INSTALL_MANUAL else []

        if self.immutable_state:
            if begin_state in ['undeployed', 'unconfigured', 'packages_installed']:
                return ['removed', 'monitored', 'managed', 'working']
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

        from chroma_core.models import Nid

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

    def set_profile(self, server_profile_id):
        '''
        Set the profile for the given host to the given profile. If the host is configured
        this includes updating the manager view and making the appropriate changes to the host.

        Otherwise it is just a case of recording the new host.

        :param server_profile_id:
        :return: List of commands required to do the job.
        '''

        server_profile = ServerProfile.objects.get(pk=server_profile_id)

        # We need fully working host to change the profile, the initial profile will be set when the host is
        # configured, once until that occurs just remember what it wants.
        if self.state in ['unconfigured', 'undeployed']:
            self.server_profile = server_profile
            self.save()

            return []
        else:
            return [{"class_name": "SetHostProfileJob",
                     "args": {"host": self,
                              "server_profile": server_profile}}]

    @property
    def pacemaker_configuration(self):
        '''
        We can't rely on the standard related_name functionality because it doesn't (as far as I can tell) allow us to
        return None when there is no forward reference. So for now we have to place this reference reference handles in
        that return none if there is no reference
        :return: Reference to object or None if not object.
        '''
        try:
            return self._pacemaker_configuration
        except PacemakerConfiguration.DoesNotExist:
            return None

    @property
    def corosync_configuration(self):
        '''
        We can't rely on the standard related_name functionality because it doesn't (as far as I can tell) allow us to
        return None when there is no forward reference. So for now we have to place this reference reference handles in
        that return none if there is no reference
        :return: Reference to object or None if not object.
        '''
        try:
            return self._corosync_configuration
        except CorosyncConfiguration.DoesNotExist:
            return None

    @property
    def ntp_configuration(self):
        '''
        We can't rely on the standard related_name functionality because it doesn't (as far as I can tell) allow us to
        return None when there is no forward reference. So for now we have to place this reference reference handles in
        that return none if there is no reference
        :return: Reference to object or None if not object.
        '''
        try:
            return self._ntp_configuration
        except NTPConfiguration.DoesNotExist:
            return None

    @property
    def rsyslog_configuration(self):
        '''
        We can't rely on the standard related_name functionality because it doesn't (as far as I can tell) allow us to
        return None when there is no forward reference. So for now we have to place this reference reference handles in
        that return none if there is no reference
        :return: Reference to object or None if not object.
        '''
        try:
            return self._rsyslog_configuration
        except RSyslogConfiguration.DoesNotExist:
            return None


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


class DeployStep(Step):
    # TODO: This timeout is the time to wait for the agent to successfully connect back to the manager. It is stupidly long
    # because we have seen the agent take stupidly long times to connect back to the manager. I've raised HYD-4769
    # to address the need for this long time out.
    DEPLOY_STARTUP_TIMEOUT = 360

    def run(self, kwargs):
        from chroma_core.services.job_scheduler.agent_rpc import AgentSsh
        from chroma_core.services.job_scheduler.agent_rpc import AgentException

        host = kwargs['host']

        # TODO: before kicking this off, check if an existing agent install is present:
        # the decision to clear it out/reset it should be something explicit maybe
        # even requiring user permission
        agent_ssh = AgentSsh(host.fqdn)
        auth_args = agent_ssh.construct_ssh_auth_args(kwargs['__auth_args']['root_pw'],
                                                      kwargs['__auth_args']['pkey'],
                                                      kwargs['__auth_args']['pkey_pw'])

        rc, stdout, stderr = agent_ssh.ssh('curl -k %s/agent/setup/%s/%s | python' % (settings.SERVER_HTTP_URL,
                                                                                      kwargs['token'].secret,
                                                                                      '?profile_name=%s' % kwargs['profile_name']),
                                           auth_args=auth_args)

        if rc == 0:
            try:
                json.loads(stdout)
            except ValueError:
                # Not valid JSON
                raise AgentException(host.fqdn,
                                     "DeployAgent",
                                     kwargs,
                                     help_text["deploy_failed_to_register_host"] % (host.fqdn, rc, stdout, stderr))
        else:
            raise AgentException(host.fqdn,
                                 "DeployAgent",
                                 kwargs,
                                 help_text["deploy_failed_to_register_host"] % (host.fqdn, rc, stdout, stderr))

        # No wait for the agent to actually connect back to the manager.
        from chroma_core.services.job_scheduler.agent_rpc import AgentRpc
        if not AgentRpc.await_session(host.fqdn, self.DEPLOY_STARTUP_TIMEOUT):
            raise AgentException(host.fqdn,
                                 "DeployAgent",
                                 kwargs,
                                 help_text["deployed_agent_failed_to_contact_manager"] % host.fqdn)


class AwaitRebootStep(Step):
    def run(self, kwargs):
        from chroma_core.services.job_scheduler.agent_rpc import AgentRpc

        AgentRpc.await_restart(kwargs['host'].fqdn, kwargs['timeout'])


class DeployHostJob(StateChangeJob):
    """Handles Deployment of the IML agent code base to a new host"""

    state_transition = StateChangeJob.StateTransition(ManagedHost, 'undeployed', 'unconfigured')
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
                'host': self.managed_host,
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
        repos = kwargs['repos']

        package_report = self.invoke_agent_expect_result(host,
                                                         'install_packages',
                                                         {'repos': repos,
                                                          'packages': packages,
                                                          'force_dependencies': True})

        if package_report:
            updates_available = package.update(host, package_report)
            UpdatesAvailableAlert.notify(host, updates_available)


class InstallHostPackagesJob(StateChangeJob):
    state_transition = StateChangeJob.StateTransition(ManagedHost, 'unconfigured', 'packages_installed')
    stateful_object = 'managed_host'
    managed_host = models.ForeignKey(ManagedHost)
    state_verb = None

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    @classmethod
    def long_description(cls, stateful_object):
        return help_text['install_packages_on_host_long']

    def description(self):
        return help_text['install_packages_on_host'] % self.managed_host

    def get_steps(self):
        '''
        This is a workaround for the fact that the object for a stateful object is not updated before the job runs, it
        is a snapshot of the object when the job was requested. This seems wrong to me and something that I will endeavour
        to understand and put right. Couple with that is the fact that strangely John took a reference to the object at
        creation time meaning that is the Stateful object was re-read the reference _so_cache is invalid.

        What is really needed is self._managed_host.refresh() which updates the values in managed_host without creating
        a new managed host instance. For today this works and I will think about this an improve it for 3.0
        '''
        self._so_cache = self.managed_host = ObjectCache.update(self.managed_host)

        steps = [(SetHostProfileStep, {'host': self.managed_host,
                                       'server_profile': self.managed_host.server_profile})]

        if self.managed_host.is_lustre_server:
            steps.append((LearnDevicesStep, {'host': self.managed_host}))

        if self.managed_host.is_managed:
            steps.extend([
                (InstallPackagesStep, {'repos': [b['bundle_name'] for b in self.managed_host.server_profile.bundles.all().values('bundle_name')],
                                       'host': self.managed_host,
                                       'packages': list(self.managed_host.server_profile.packages) + ['chroma-agent-management']}),
                (RebootIfNeededStep, {'host': self.managed_host,
                                      'timeout': settings.INSTALLATION_REBOOT_TIMEOUT})
            ])

        return steps


class SetupHostJob(NullStateChangeJob):
    target_object = models.ForeignKey(ManagedHost)
    state_transition = StateChangeJob.StateTransition(ManagedHost, 'packages_installed', 'managed')
    _long_description = help_text['setup_managed_host']
    state_verb = 'Setup managed server'

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    def get_deps(self):
        # It really does not feel right that this is in here, but it does sort of work. These are the things
        # it is dependent on so create them. Also I can't work out with today's state machine anywhere else to
        # put them that works.
        if self.target_object.pacemaker_configuration is None:
            pacemaker_configuration, _ = PacemakerConfiguration.objects.get_or_create(host=self.target_object)
            corosync_configuration, _ = CorosyncConfiguration.objects.get_or_create(host=self.target_object)
            ntp_configuration, _ = NTPConfiguration.objects.get_or_create(host=self.target_object)
            rsyslog_configuration, _ = RSyslogConfiguration.objects.get_or_create(host=self.target_object)

            ObjectCache.add(CorosyncConfiguration, corosync_configuration)
            ObjectCache.add(PacemakerConfiguration, pacemaker_configuration)
            ObjectCache.add(NTPConfiguration, ntp_configuration)
            ObjectCache.add(RSyslogConfiguration, rsyslog_configuration)

        deps = []

        if self.target_object.lnet_configuration:
            deps.append(DependOn(self.target_object.lnet_configuration, 'lnet_up'))

        if self.target_object.pacemaker_configuration:
            deps.append(DependOn(self.target_object.pacemaker_configuration, 'started'))

        if self.target_object.ntp_configuration:
            deps.append(DependOn(self.target_object.ntp_configuration, 'configured'))

        if self.target_object.rsyslog_configuration:
            deps.append(DependOn(self.target_object.rsyslog_configuration, 'configured'))

        return DependAll(deps)

    def description(self):
        return help_text['setup_managed_host_on'] % self.target_object

    @classmethod
    def can_run(cls, host):
        return host.is_managed and not host.is_worker


class SetupMonitoredHostJob(NullStateChangeJob):
    target_object = models.ForeignKey(ManagedHost)
    state_transition = StateChangeJob.StateTransition(ManagedHost, 'packages_installed', 'monitored')
    _long_description = help_text['setup_monitored_host']
    state_verb = 'Setup monitored server'

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    def get_deps(self):
        # Moving out of unconfigured will mean that lnet will start monitoring and responding to the state.
        return DependOn(self.target_object.lnet_configuration, 'lnet_unloaded', unacceptable_states=['unconfigured'])

    def description(self):
        return help_text['setup_monitored_host_on'] % self.target_object

    @classmethod
    def can_run(cls, host):
        return host.is_monitored


class SetupWorkertJob(NullStateChangeJob):
    target_object = models.ForeignKey(ManagedHost)
    state_transition = StateChangeJob.StateTransition(ManagedHost, 'packages_installed', 'working')
    _long_description = help_text['setup_worker_host']
    state_verb = 'Setup worker node'

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    def get_deps(self):
        # Moving out of unconfigured will mean that lnet will start monitoring and responding to the state.
        return DependOn(self.target_object.lnet_configuration, 'lnet_unloaded', unacceptable_states=['unconfigured'])

    def description(self):
        return help_text['setup_worker_host_on'] % self.target_object

    @classmethod
    def can_run(cls, host):
        return host.is_managed and host.is_worker


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
            volume_nodes = VolumeNode.objects.filter(host = host)
            target_devices = []

            for volume_node in volume_nodes:
                resource = volume_node.volume.storage_resource.to_resource()
                try:
                    uuid = resource.uuid
                except AttributeError:
                    uuid = None

                target_devices.append({"path": volume_node.path,
                                       "type": resource.device_type(),
                                       "uuid": uuid})

            with transaction.commit_on_success():
                self.log("Scanning server %s..." % host)
            data = self.invoke_agent(host, 'detect_scan', {"target_devices": target_devices})
            host_data[host] = data

        with transaction.commit_on_success():
            DetectScan(self).run(host_data)


class DetectTargetsJob(HostListMixin):
    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    @classmethod
    def long_description(cls, stateful_object):
        return help_text['detect_targets']

    def description(self):
        return "Scan for Lustre targets"

    def get_steps(self):
        return [(UpdateDevicesStep, {'host': host}) for host in self.hosts] + \
               [(DetectTargetsStep, {'host_ids': [h.id for h in self.hosts]})]


class SetHostProfileStep(Step):
    database = True

    def is_dempotent(self):
        return True

    def run(self, kwargs):
        from chroma_core.services.job_scheduler.agent_rpc import AgentRpc

        host = kwargs['host']
        server_profile = kwargs['server_profile']

        self.invoke_agent_expect_result(host, 'update_profile', {"profile": server_profile.as_dict})

        job_scheduler_notify.notify(host,
                                  tznow(),
                                  {'server_profile_id': server_profile.id})

        job_scheduler_notify.notify(host,
                                  tznow(),
                                  {'immutable_state': not server_profile.managed})

        # If we have installed any updates at all, then assume it is necessary to restart the agent, as
        # they could be things the agent uses/imports or API changes, specifically to kernel_status() below
        old_session_id = AgentRpc.get_session_id(host.fqdn)
        self.invoke_agent(host, 'restart_agent')
        AgentRpc.await_restart(host.fqdn, timeout=settings.AGENT_RESTART_TIMEOUT, old_session_id=old_session_id)

    @classmethod
    def describe(cls, kwargs):
        return help_text["set_host_profile_on"] % kwargs['host']


class SetHostProfileJob(Job):
    host = models.ForeignKey(ManagedHost)
    server_profile = models.ForeignKey(ServerProfile)

    @classmethod
    def long_description(cls, stateful_object):
        return help_text['set_host_profile_on'] % stateful_object

    def description(self):
        return "Set profile and update host %s" % self.host.nodename

    def get_steps(self):
        return [(SetHostProfileStep, {'host': self.host,
                                      'server_profile': self.server_profile})]

    def create_locks(self):
        return [StateLock(
            job = self,
            locked_item = self.host,
            write = True
        )]

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']


class UpdateDevicesJob(HostListMixin):
    @classmethod
    def long_description(cls, stateful_object):
        return help_text['update_devices']

    def description(self):
        return "Update the device info held for hosts %s" % ",".join([h.fqdn for h in self.hosts])

    def get_deps(self):
        return DependAll(DependOn(host.lnet_configuration, 'lnet_up') for host in self.hosts)

    def get_steps(self):
        return [(UpdateDevicesStep, {'host': host})
                for host in self.hosts]

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']


class DeleteHostStep(Step):
    idempotent = True
    database = True

    def run(self, kwargs):
        from chroma_core.models import package
        from chroma_core.services.http_agent import HttpAgentRpc
        from chroma_core.services.job_scheduler.agent_rpc import AgentRpc

        host = kwargs['host']
        # First, cut off any more incoming connections
        # TODO: populate a CRL and send a nginx HUP signal to reread it

        # Delete anything that is dependent on us.
        for object in host.get_dependent_objects(inclusive=True):
            # We are allowed to modify state directly because we have locked these objects
            job_log.info("Deleting dependent %s for host %s" % (object, host))
            object.cancel_current_operations()
            object.set_state('removed')
            object.mark_deleted()
            object.save()

        # Third, terminate any currently open connections and ensure there is nothing in a queue
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
    state_transition = StateChangeJob.StateTransition(ManagedHost, ['unconfigured', 'managed', 'monitored', 'working'], 'removed')
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
    def long_description(cls, host):
        if host.is_monitored:
            return help_text['remove_monitored_configured_server']

        if host.is_managed:
            return help_text['remove_configured_server']

        raise NotImplemented("Host is of unknown configuration")

    def get_confirmation_string(self):
        return RemoveHostJob.long_description(self.host)

    def description(self):
        return "Remove host %s from configuration" % self.host

    def get_deps(self):
        deps = []

        if self.host.lnet_configuration:
            deps.append(DependOn(self.host.lnet_configuration, 'unconfigured'))

        if self.host.corosync_configuration:
            deps.append(DependOn(self.host.corosync_configuration, 'unconfigured'))

        if self.host.ntp_configuration:
            deps.append(DependOn(self.host.ntp_configuration, 'unconfigured'))

        if self.host.rsyslog_configuration:
            deps.append(DependOn(self.host.rsyslog_configuration, 'unconfigured'))

        return DependAll(deps)

    def get_steps(self):
        return [(RemoveServerConfStep, {'host': self.host}),
                (DeleteHostStep, {'host': self.host, 'force': False})]


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

        # Take a write lock on get_stateful_object if this is a StateChangeJob
        for object in self.host.get_dependent_objects(inclusive=True):
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
        return DependAny([DependOn(self.host, 'managed', acceptable_states=self.host.not_state('removed')),
                          DependOn(self.host, 'monitored', acceptable_states=self.host.not_state('removed')),
                          DependOn(self.host, 'working', acceptable_states=self.host.not_state('removed'))])

    def get_steps(self):
        return [(DeleteHostStep, {'host': self.host, 'force': True})]

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
        return (host.is_managed and
                host.state not in ['removed', 'undeployed', 'unconfigured'] and
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
        return (host.is_managed and
               host.state not in ['removed', 'undeployed', 'unconfigured'] and
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
    state_transition = StateChangeJob.StateTransition(ManagedHost, 'unconfigured', 'removed')
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
    # REMEMBER: This runs against the old agent and so any API changes need to be compatible with
    # all agents that we might want to upgrade from. Forget this at your peril.
    # Require database because we update package records
    database = True

    def run(self, kwargs):
        from chroma_core.models import package
        from chroma_core.services.job_scheduler.agent_rpc import AgentRpc

        host = kwargs['host']
        package_report = self.invoke_agent_expect_result(host,
                                                         'update_packages',
                                                         {'repos': kwargs['bundles'],
                                                          'packages': kwargs['packages']})

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
            if host.pacemaker_configuration:
                # Upgrade of pacemaker packages could have left it disabled
                self.invoke_agent(kwargs['host'], 'enable_pacemaker')
                # and not running,
                self.invoke_agent(kwargs['host'], 'start_pacemaker')

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
        # Two stage update, first update the agent - then update everything. This means that when the packages are
        # updated the new agent is used.
        return [
            (UpdatePackagesStep, {
                'host': self.host,
                'bundles': ['iml-agent'],
                'packages': [],
            }),
            (UpdatePackagesStep, {
                'host': self.host,
                'bundles': [b['bundle_name'] for b in self.host.server_profile.bundles.all().values('bundle_name')],
                'packages': list(self.host.server_profile.packages)
            })
        ]

    def create_locks(self):
        locks = [StateLock(
            job = self,
            locked_item = self.host,
            write = True
        )]

        # Take a write lock on get_stateful_object if this is a StateChangeJob
        for object in self.host.get_dependent_objects():
            job_log.debug("Creating StateLock on %s/%s" % (object.__class__, object.id))
            locks.append(StateLock(
                job = self,
                locked_item = object,
                write = True))

        return locks

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


class UpdateNidsJob(HostListMixin):
    @classmethod
    def long_description(cls, stateful_object):
        return help_text["update_nids"]

    def description(self):
        if len(self.hosts) > 1:
            return "Update NIDs on %d hosts" % len(self.hosts)
        else:
            return "Update NIDs on host %s" % self.hosts[0]

    def _targets_on_hosts(self):
        from chroma_core.models.target import ManagedMgs, ManagedTarget, FilesystemMember
        from chroma_core.models.filesystem import ManagedFilesystem

        filesystems = set()
        targets = set()
        for target in ManagedTarget.objects.filter(managedtargetmount__host__in = self.hosts):
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
            [DependOn(host.lnet_configuration, 'lnet_up') for host in target_primary_hosts] +
            [DependOn(fs, 'stopped') for fs in filesystems] +
            [DependOn(t, 'unmounted') for t in targets]
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
