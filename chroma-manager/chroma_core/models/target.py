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
import uuid
from chroma_core.lib.cache import ObjectCache

from django.db import models, transaction
from chroma_core.lib.job import DependOn, DependAny, DependAll, Step, job_log
from chroma_core.models.alert import AlertState
from chroma_core.models.event import AlertEvent
from chroma_core.models.jobs import StateChangeJob, StateLock, AdvertisedJob
from chroma_core.models.host import ManagedHost, VolumeNode, Volume, HostContactAlert
from chroma_core.models.jobs import StatefulObject
from chroma_core.models.utils import DeletableMetaclass, DeletableDowncastableMetaclass, MeasuredEntity
from chroma_help.help import help_text
from chroma_core.chroma_common.blockdevices.blockdevice import BlockDevice
from chroma_core.chroma_common.filesystems.filesystem import FileSystem
import settings


class NotAFileSystemMember(Exception):
    pass


class FilesystemMember(models.Model):
    """A Mountable for a particular filesystem, such as
       MDT, OST or Client"""
    filesystem = models.ForeignKey('ManagedFilesystem')
    index = models.IntegerField()

    # Use of abstract base classes to avoid django bug #12002
    class Meta:
        abstract = True


# select_description
#
# This little nugget selects from a dict of class: description to
# return the description that matches the that class or subclass in the
# key
#
# Probably called like this
#
# select_description(stateful_object,
#                    {ManagedOst: help_text["stop_ost"],
#                     ManagedMgs: help_text["stop_mgt"],
#                     ManagedMdt: help_text["stop_mdt"]})
def select_description(stateful_object, descriptions):
    def match(class_to_compare):
        return issubclass(stateful_object.downcast_class, class_to_compare)

    for class_to_compare, desc in descriptions.iteritems():
        if match(class_to_compare):
            return desc

    match_class_names = ", ".join(class_to_compare.__name__ for class_to_compare in descriptions.keys())

    raise RuntimeError("Could not find %s in %s" % (stateful_object.downcast_class.__name__, match_class_names))


class ManagedTarget(StatefulObject):
    __metaclass__ = DeletableDowncastableMetaclass
    name = models.CharField(max_length = 64, null = True, blank = True,
                            help_text = "Lustre target name, e.g. 'testfs-OST0001'.  May be null\
                            if the target has not yet been registered.")

    uuid = models.CharField(max_length = 64, null = True, blank = True,
                            help_text = "UUID of the target's internal file system.  May be null\
                            if the target has not yet been formatted")

    ha_label = models.CharField(max_length = 64, null = True, blank = True,
                                help_text = "Label used for HA layer; human readable but unique")

    volume = models.ForeignKey('Volume')

    inode_size = models.IntegerField(null = True, blank = True, help_text = "Size in bytes per inode")
    bytes_per_inode = models.IntegerField(null = True, blank = True, help_text = "Constant used during formatting to "
                                          "determine inode count by dividing the volume size by ``bytes_per_inode``")
    inode_count = models.BigIntegerField(null = True, blank = True, help_text = "The number of inodes in this target's"
                                         "backing store")

    def get_hosts(self, primary=True):
        """Getting all the hosts, and filtering in python is less db hits"""

        mounts = self.managedtargetmount_set.all()

        failovers = []
        for mount in mounts:
            if primary:
                if mount.primary:
                    return mount.host
            else:
                if not mount.primary:
                    failovers.append(mount.host)

        return failovers

    reformat = models.BooleanField(
        help_text = "Only used during formatting, indicates that when formatting this target \
        any existing filesystem on the Volume should be overwritten")

    def primary_server(self):
        return self.get_hosts(primary=True)

    @property
    def full_volume(self):
        """Used in API Resource that want the Volume and all related objects

        This results in a join query to get data with fewer DB hits
        """

        return Volume.objects.all().select_related(
            'storage_resource',
            'storage_resource__resource_class',
            'storage_resource__resource_class__storage_plugin'
        ).prefetch_related('volumenode_set', 'volumenode_set__host').get(pk=self.volume.pk)

    def secondary_servers(self):
        return [tm.host for tm in self.managedtargetmount_set.filter(primary = False)]

    def update_active_mount(self, nodename):
        """Set the active_mount attribute from the nodename of a host, raising
        RuntimeErrors if the host doesn't exist or doesn't have a ManagedTargetMount"""
        try:
            started_on = ObjectCache.get_one(ManagedHost, lambda mh: mh.nodename == nodename)
        except ManagedHost.DoesNotExist:
            raise RuntimeError("Target %s (%s) found on host %s, which is not a ManagedHost" % (self, self.id, nodename))
        try:
            job_log.debug("Started %s on %s" % (self.ha_label, started_on))
            target_mount = ObjectCache.get_one(ManagedTargetMount, lambda mtm: mtm.target_id == self.id and mtm.host_id == started_on.id)
            self.active_mount = target_mount
        except ManagedTargetMount.DoesNotExist:
            job_log.error("Target %s (%s) found on host %s (%s), which has no ManagedTargetMount for this self" % (self, self.id, started_on, started_on.pk))
            raise RuntimeError("Target %s reported as running on %s, but it is not configured there" % (self, started_on))

    def get_param(self, key):
        params = self.targetparam_set.filter(key = key)
        return [p.value for p in params]

    def get_params(self):
        return [(p.key, p.value) for p in self.targetparam_set.all()]

    def get_failover_nids(self):
        fail_nids = []
        for secondary_mount in self.managedtargetmount_set.filter(primary = False):
            host = secondary_mount.host
            failhost_nids = host.lnetconfiguration.get_nids()
            assert(len(failhost_nids) != 0)
            fail_nids.extend(failhost_nids)
        return fail_nids

    @property
    def default_mount_point(self):
        return "/mnt/%s" % self.name

    @property
    def primary_host(self):
        return self.get_hosts(primary=True)

    @property
    def failover_hosts(self):
        return self.get_hosts(primary=False)

    @property
    def active_host(self):
        if self.active_mount:
            return self.active_mount.host
        else:
            return None

    def get_label(self):
        return self.name

    def __str__(self):
        return self.name or ''

    def best_available_host(self):
        """
        :return: A host which is available for actions, preferably the primary.
        """
        mounts = ObjectCache.get(ManagedTargetMount, lambda mtm: mtm.target.id == self.id)
        for mount in sorted(mounts, lambda a, b: cmp(b.primary, a.primary)):
            if HostContactAlert.filter_by_item(mount.host).count() == 0:
                return mount.host

        raise ManagedHost.DoesNotExist("No hosts online for %s" % self)

    # unformatted: I exist in theory in the database
    # formatted: I've been mkfs'd
    # registered: I've registered with the MGS, I'm not setup in HA yet
    # unmounted: I'm set up in HA, ready to mount
    # mounted: Im mounted
    # removed: this target no longer exists in real life
    # forgotten: Equivalent of 'removed' for immutable_state targets
    # Additional states needed for 'deactivated'?
    states = ['unformatted', 'formatted', 'registered', 'unmounted', 'mounted', 'removed', 'forgotten']
    initial_state = 'unformatted'
    active_mount = models.ForeignKey('ManagedTargetMount', blank = True, null = True)

    def set_state(self, state, intentional = False):
        job_log.debug("mt.set_state %s %s" % (state, intentional))
        super(ManagedTarget, self).set_state(state, intentional)
        if intentional:
            TargetOfflineAlert.notify_warning(self, self.state == 'unmounted')
        else:
            TargetOfflineAlert.notify(self, self.state == 'unmounted')

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    def get_deps(self, state = None):
        from chroma_core.models import ManagedFilesystem
        if not state:
            state = self.state

        deps = []
        if state == 'mounted' and self.active_mount and not self.immutable_state:
            # Depend on the active mount's host having LNet up, so that if
            # LNet is stopped on that host this target will be stopped first.
            target_mount = self.active_mount
            host = ObjectCache.get_one(ManagedHost, lambda mh: mh.id == target_mount.host_id)
            deps.append(DependOn(host, 'lnet_up', fix_state='unmounted'))

            # TODO: also express that this situation may be resolved by migrating
            # the target instead of stopping it.

        if issubclass(self.downcast_class, FilesystemMember) and state not in ['removed', 'forgotten']:
            # Make sure I follow if filesystem goes to 'removed'
            # or 'forgotten'
            # FIXME: should get filesystem membership from objectcache
            filesystem_id = self.downcast().filesystem_id
            filesystem = ObjectCache.get_by_id(ManagedFilesystem, filesystem_id)
            deps.append(DependOn(filesystem, 'available',
                                 acceptable_states = filesystem.not_states(['forgotten', 'removed']), fix_state=lambda s: s))

        if state not in ['removed', 'forgotten']:
            target_mounts = ObjectCache.get(ManagedTargetMount, lambda mtm: mtm.target_id == self.id)
            for tm in target_mounts:
                host = ObjectCache.get_by_id(ManagedHost, tm.host_id)
                if self.immutable_state:
                    deps.append(DependOn(host, 'lnet_up', acceptable_states = list(set(host.states) - set(['removed', 'forgotten'])), fix_state = 'forgotten'))
                else:
                    deps.append(DependOn(host, 'lnet_up', acceptable_states = list(set(host.states) - set(['removed', 'forgotten'])), fix_state = 'removed'))

        return DependAll(deps)

    reverse_deps = {
        'ManagedTargetMount': lambda mtm: ObjectCache.mtm_targets(mtm.id),
        'ManagedHost': lambda mh: ObjectCache.host_targets(mh.id),
        'ManagedFilesystem': lambda mfs: ObjectCache.fs_targets(mfs.id),
        'Copytool': lambda ct: ObjectCache.client_mount_copytools(ct.id)
    }

    @classmethod
    def create_for_volume(cls, volume_id, create_target_mounts = True, **kwargs):
        # Local imports to avoid inter-model import dependencies
        volume = Volume.objects.get(pk = volume_id)

        target = cls(**kwargs)
        target.volume = volume

        # Acquire a target index for FilesystemMember targets, and
        # populate `name`
        if issubclass(cls, ManagedMdt):
            index = target.filesystem.mdt_next_index
            target.name = "%s-MDT%04x" % (target.filesystem.name, index)
            target.index = index
            target.filesystem.mdt_next_index += 1
            target.filesystem.save()
        elif issubclass(cls, ManagedOst):
            index = target.filesystem.ost_next_index
            target.name = "%s-OST%04x" % (target.filesystem.name, index)
            target.index = index
            target.filesystem.ost_next_index += 1
            target.filesystem.save()
        else:
            target.name = "MGS"

        target.save()

        target_mounts = []

        def create_target_mount(volume_node):
            mount = ManagedTargetMount(
                volume_node = volume_node,
                target = target,
                host = volume_node.host,
                mount_point = target.default_mount_point,
                primary = volume_node.primary)
            mount.save()
            target_mounts.append(mount)

        if create_target_mounts:
            try:
                primary_volume_node = volume.volumenode_set.get(primary = True, host__not_deleted = True)
                create_target_mount(primary_volume_node)
            except VolumeNode.DoesNotExist:
                raise RuntimeError("No primary lun_node exists for volume %s, cannot create target" % volume.id)
            except VolumeNode.MultipleObjectsReturned:
                raise RuntimeError("Multiple primary lun_nodes exist for volume %s, internal error" % volume.id)

            for secondary_volume_node in volume.volumenode_set.filter(use = True, primary = False, host__not_deleted = True):
                create_target_mount(secondary_volume_node)

        return target, target_mounts

    def target_type(cls):
        raise "Unimplemented method 'target_type'"

    def mkfs_override_options(self, filesystemtype, mkfs_options):
        """ Allows a ManagedTarget to modify the mkfs_options as required.
        :return: A list of additional options for mkfs as in those things that appear after --mkfsoptions
        """
        return mkfs_options


class ManagedOst(ManagedTarget, FilesystemMember, MeasuredEntity):
    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    def get_available_states(self, begin_state):
        # Exclude the transition to 'removed' in favour of being removed when our FS is
        if self.immutable_state:
            return []
        else:
            available_states = super(ManagedOst, self).get_available_states(begin_state)
            available_states = list(set(available_states) ^ set(['forgotten']))
            return available_states

    def target_type(cls):
        return "ost"

    def mkfs_override_options(self, filesystemtype, mkfs_options):
        if (settings.JOURNAL_SIZE != None) and (filesystemtype == 'ldiskfs'):
            mkfs_options.append("-J size=%s" % settings.JOURNAL_SIZE)

        # HYD-1089 should supercede these settings
        if settings.LUSTRE_MKFS_OPTIONS_OST:
            mkfs_options = [settings.LUSTRE_MKFS_OPTIONS_OST]

        return mkfs_options


class ManagedMdt(ManagedTarget, FilesystemMember, MeasuredEntity):
    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    def get_available_states(self, begin_state):
        # Exclude the transition to 'removed' in favour of being removed when our FS is
        if self.immutable_state:
            return []
        else:
            available_states = super(ManagedMdt, self).get_available_states(begin_state)
            available_states = list(set(available_states) - set(['removed', 'forgotten']))

            return available_states

    def target_type(cls):
        return "mdt"

    def mkfs_override_options(self, filesystemtype, mkfs_options):
        if (settings.JOURNAL_SIZE != None) and (filesystemtype == 'ldiskfs'):
            mkfs_options += ["-J size=%s" % settings.JOURNAL_SIZE]

        # HYD-1089 should supercede these settings
        if settings.LUSTRE_MKFS_OPTIONS_MDT:
            mkfs_options = [settings.LUSTRE_MKFS_OPTIONS_MDT]

        return mkfs_options


class ManagedMgs(ManagedTarget, MeasuredEntity):
    conf_param_version = models.IntegerField(default = 0)
    conf_param_version_applied = models.IntegerField(default = 0)

    def get_available_states(self, begin_state):
        if self.immutable_state:
            if self.managedfilesystem_set.count() == 0:
                return ['forgotten']
            else:
                return []
        else:
            available_states = super(ManagedMgs, self).get_available_states(begin_state)

            # Exclude the transition to 'forgotten' because immutable_state is False
            available_states = list(set(available_states) - set(['forgotten']))

            # Only advertise removal if the FS has already gone away
            if self.managedfilesystem_set.count() > 0:
                available_states = list(set(available_states) - set(['removed']))
                if 'removed' in available_states:
                    available_states.remove('removed')

            return available_states

    @classmethod
    def get_by_host(cls, host):
        return cls.objects.get(managedtargetmount__host = host)

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    def nids(self):
        """Returns a tuple of per-host NID strings tuples"""
        host_nids = []
        # Note: order by -primary in order that the first argument passed to mkfs
        # in failover configurations is the primary mount -- Lustre will use the
        # first --mgsnode argument as the NID to connect to for target registration,
        # and if that is the secondary NID then bad things happen during first
        # filesystem start.
        for target_mount in self.managedtargetmount_set.all().order_by('-primary'):
            host = target_mount.host
            host_nids.append(tuple(host.lnetconfiguration.get_nids()))

        return tuple(host_nids)

    def set_conf_params(self, params, new = True):
        """
        :param new: If False, do not increment the conf param version number, resulting in
                    new conf params not immediately being applied to the MGS (use if importing
                    records for an already configured filesystem).
        :param params: is a list of unsaved ConfParam objects"""
        version = None
        from django.db.models import F
        if new:
            ManagedMgs.objects.filter(pk = self.id).update(conf_param_version = F('conf_param_version') + 1)
        version = ManagedMgs.objects.get(pk = self.id).conf_param_version
        for p in params:
            p.version = version
            p.save()

    def target_type(cls):
        return "mgs"

    def mkfs_override_options(self, filesystemtype, mkfs_options):
        # HYD-1089 should supercede these settings
        if settings.LUSTRE_MKFS_OPTIONS_MGS:
            mkfs_options = [settings.LUSTRE_MKFS_OPTIONS_MGS]

        return mkfs_options


class TargetRecoveryInfo(models.Model):
    """Record of what we learn from /proc/fs/lustre/*/*/recovery_status
       for a running target"""
    #: JSON-encoded dict parsed from /proc
    recovery_status = models.TextField()

    target = models.ForeignKey('chroma_core.ManagedTarget')

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    @staticmethod
    @transaction.commit_on_success
    def update(target, recovery_status):
        TargetRecoveryInfo.objects.filter(target = target).delete()
        instance = TargetRecoveryInfo.objects.create(
            target = target,
            recovery_status = json.dumps(recovery_status))
        return instance.is_recovering(recovery_status)

    def is_recovering(self, data = None):
        if not data:
            data = json.loads(self.recovery_status)
        return ("status" in data and data["status"] == "RECOVERING")

    #def recovery_status_str(self):
    #    data = json.loads(self.recovery_status)
    #    if 'status' in data and data["status"] == "RECOVERING":
    #        return "%s %ss remaining" % (data["status"], data["time_remaining"])
    #    elif 'status' in data:
    #        return data["status"]
    #    else:
    #        return "N/A"


def _delete_target(target):
    if issubclass(target.downcast_class, ManagedMgs):
        from chroma_core.models.filesystem import ManagedFilesystem
        assert ManagedFilesystem.objects.filter(mgs = target).count() == 0
    target.mark_deleted()
    job_log.debug("_delete_target: %s %s" % (target, id(target)))

    if target.volume.storage_resource is None:
        # If a LogicalDrive storage resource goes away, but the
        # volume is in use by a target, then the volume is left behind.
        # Check if this is the case, and clean up any remaining volumes.
        for vn in VolumeNode.objects.filter(volume = target.volume):
            vn.mark_deleted()
        target.volume.mark_deleted()


class RemoveConfiguredTargetJob(StateChangeJob):
    state_transition = (ManagedTarget, 'unmounted', 'removed')
    stateful_object = 'target'
    state_verb = "Remove"
    target = models.ForeignKey(ManagedTarget)

    @classmethod
    def long_description(cls, stateful_object):
        return select_description(stateful_object, {ManagedOst: help_text["remove_ost"],
                                                    ManagedMgs: help_text["remove_mgt"]})

    def get_requires_confirmation(self):
        return True

    def get_confirmation_string(self):
        if issubclass(self.target.downcast_class, ManagedOst):
            return "Remove the OST from the file system. It will no longer be seen in Chroma Manager. Before removing the OST, manually remove all data from the OST. When an OST is removed, files stored on the OST will no longer be accessible."
        else:
            return None

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    def description(self):
        return "Remove target %s from configuration" % (self.target)

    def get_deps(self):
        deps = []

        return DependAll(deps)

    def get_steps(self):
        # TODO: actually do something with Lustre before deleting this from our DB
        steps = []
        for target_mount in self.target.managedtargetmount_set.all().order_by('primary'):
            steps.append((UnconfigurePacemakerStep, {
                'target_mount': target_mount,
                'target': target_mount.target,
                'host': target_mount.host
            }))
        for target_mount in self.target.managedtargetmount_set.all().order_by('primary'):
            steps.append((UnconfigureTargetStoreStep, {
                'target_mount': target_mount,
                'target': target_mount.target,
                'host': target_mount.host
            }))
        return steps

    def on_success(self):
        _delete_target(self.target)
        super(RemoveConfiguredTargetJob, self).on_success()


# HYD-832: when transitioning from 'registered' to 'removed', do something to
# remove this target from the MGS
class RemoveTargetJob(StateChangeJob):
    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    state_transition = (ManagedTarget, ['unformatted', 'formatted', 'registered'], 'removed')
    stateful_object = 'target'
    state_verb = "Remove"
    target = models.ForeignKey(ManagedTarget)

    @classmethod
    def long_description(cls, stateful_object):
        return select_description(stateful_object, {ManagedOst: help_text["remove_ost"],
                                                    ManagedMgs: help_text["remove_mgt"]})

    def description(self):
        return "Remove target %s from configuration" % (self.target)

    def get_confirmation_string(self):
        if issubclass(self.target.downcast_class, ManagedOst):
            if self.target.state == 'registered':
                return "Remove the OST from the file system. It will no longer be seen in Chroma Manager. Before removing the OST, manually remove all data from the OST. When an OST is removed, files stored on the OST will no longer be accessible."
            else:
                return None
        else:
            return None

    def get_requires_confirmation(self):
        return True

    def on_success(self):
        _delete_target(self.target)

        super(RemoveTargetJob, self).on_success()


class ForgetTargetJob(StateChangeJob):
    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    @classmethod
    def long_description(cls, stateful_object):
        return select_description(stateful_object, {ManagedOst: help_text["remove_ost"],
                                                    ManagedMgs: help_text["remove_mgt"]})

    def description(self):
        return "Forget unmanaged target %s" % self.target

    def get_requires_confirmation(self):
        return True

    def on_success(self):
        _delete_target(self.target)

        super(ForgetTargetJob, self).on_success()

    state_transition = (ManagedTarget, ['unmounted', 'mounted'], 'forgotten')
    stateful_object = 'target'
    state_verb = "Forget"
    target = models.ForeignKey(ManagedTarget)


class RegisterTargetStep(Step):
    idempotent = True

    def run(self, kwargs):
        target = kwargs['target']

        result = self.invoke_agent(kwargs['primary_host'], "register_target",
                                   {'target_name': target.name,
                                    'device_path': kwargs['device_path'],
                                    'mount_point': kwargs['mount_point'],
                                    'backfstype': kwargs['backfstype']})

        if not result['label'] == target.name:
            # We synthesize a target name (e.g. testfs-OST0001) when creating targets, then
            # pass --index to mkfs.lustre, so our name should match what is set after registration
            raise RuntimeError("Registration returned unexpected target name '%s' (expected '%s')" % (result['label'], target.name))
        job_log.debug("Registration complete, updating target %d with name=%s, ha_label=%s" % (target.id, target.name, target.ha_label))


class GenerateHaLabelStep(Step):
    idempotent = True

    def sanitize_name(self, name):
        FILTER_REGEX = r'^\d|^-|^\.|[(){}[\].:@$%&/+,;\s]+'
        sanitized_name = re.sub(FILTER_REGEX, '_', name)
        return "%s_%s" % (sanitized_name, uuid.uuid4().hex[:6])

    def run(self, kwargs):
        target = kwargs['target']
        target.ha_label = self.sanitize_name(target.name)
        job_log.debug("Generated ha_label=%s for target %s (%s)" % (target.ha_label, target.id, target.name))


class ConfigureTargetStoreStep(Step):
    idempotent = True

    def run(self, kwargs):
        target = kwargs['target']
        target_mount = kwargs['target_mount']
        volume_node = kwargs['volume_node']
        host = kwargs['host']
        backfstype = kwargs['backfstype']

        assert(volume_node is not None)

        self.invoke_agent(host, "configure_target_store", {
            'device': volume_node.path,
            'uuid': target.uuid,
            'mount_point': target_mount.mount_point,
            'backfstype': backfstype,
            'target_name': target.name})


class UnconfigureTargetStoreStep(Step):
    idempotent = True

    def run(self, kwargs):
        target = kwargs['target']
        host = kwargs['host']

        self.invoke_agent(host, "unconfigure_target_store", {
            'uuid': target.uuid})


class ConfigurePacemakerStep(Step):
    idempotent = True

    def run(self, kwargs):
        target = kwargs['target']
        target_mount = kwargs['target_mount']
        volume_node = kwargs['volume_node']
        host = kwargs['host']

        assert(volume_node is not None)

        self.invoke_agent(host, "configure_target_ha", {
            'device': volume_node.path,
            'ha_label': target.ha_label,
            'uuid': target.uuid,
            'primary': target_mount.primary,
            'mount_point': target_mount.mount_point})


class UnconfigurePacemakerStep(Step):
    idempotent = True

    def run(self, kwargs):
        target = kwargs['target']
        target_mount = kwargs['target_mount']

        self.invoke_agent(kwargs['host'], "unconfigure_target_ha",
                          {'ha_label': target.ha_label,
                           'uuid': target.uuid,
                           'primary': target_mount.primary})


class ConfigureTargetJob(StateChangeJob):
    state_transition = (ManagedTarget, 'registered', 'unmounted')
    stateful_object = 'target'
    state_verb = "Configure mount points"
    target = models.ForeignKey(ManagedTarget)

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    @classmethod
    def long_description(cls, stateful_object):
        return help_text['configure_target']

    def description(self):
        return "Configure %s mount points" % self.target

    def get_steps(self):
        steps = []

        for target_mount in self.target.managedtargetmount_set.all().order_by('-primary'):
            steps.append((ConfigureTargetStoreStep, {
                'host': target_mount.host,
                'target': target_mount.target,
                'target_mount': target_mount,
                'backfstype': target_mount.volume_node.volume.filesystem_type,
                'volume_node': target_mount.volume_node
            }))

        for target_mount in self.target.managedtargetmount_set.all().order_by('-primary'):
            steps.append((ConfigurePacemakerStep, {
                'host': target_mount.host,
                'target': target_mount.target,
                'target_mount': target_mount,
                'volume_node': target_mount.volume_node
            }))

        return steps

    def get_deps(self):
        deps = []

        prim_mtm = ObjectCache.get_one(ManagedTargetMount, lambda mtm: mtm.primary is True and mtm.target_id == self.target.id)
        deps.append(DependOn(prim_mtm.host, 'lnet_up'))

        return DependAll(deps)


class RegisterTargetJob(StateChangeJob):
    # FIXME: this really isn't ManagedTarget, it's FilesystemMember+ManagedTarget
    state_transition = (ManagedTarget, 'formatted', 'registered')
    stateful_object = 'target'
    state_verb = "Register"
    target = models.ForeignKey(ManagedTarget)

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    @classmethod
    def long_description(cls, stateful_object):
        return help_text['register_target']

    def description(self):
        return "Register %s" % self.target

    def get_steps(self):
        steps = []

        target_class = self.target.downcast_class
        if issubclass(target_class, ManagedMgs):
            steps = []
        elif issubclass(target_class, FilesystemMember):
            primary_mount = self.target.managedtargetmount_set.get(primary = True)
            path = primary_mount.volume_node.path

            mgs_id = self.target.downcast().filesystem.mgs.id
            mgs = ObjectCache.get_by_id(ManagedTarget, mgs_id)

            # Check that the active mount of the MGS is its primary mount (HYD-233 Lustre limitation)
            if not mgs.active_mount == mgs.managedtargetmount_set.get(primary = True):
                raise RuntimeError("Cannot register target while MGS is not started on its primary server")

            steps = [(RegisterTargetStep, {
                'primary_host': primary_mount.host,
                'target': self.target,
                'device_path': path,
                'mount_point': primary_mount.mount_point,
                'backfstype': primary_mount.volume_node.volume.filesystem_type
            })]
        else:
            raise NotImplementedError(target_class)

        steps.append((GenerateHaLabelStep, {'target': self.target}))

        return steps

    def get_deps(self):
        deps = []

        deps.append(DependOn(ObjectCache.target_primary_server(self.target), 'lnet_up'))

        if issubclass(self.target.downcast_class, FilesystemMember):
            # FIXME: spurious downcast, should cache filesystem associaton in objectcache
            mgs = ObjectCache.get_by_id(ManagedTarget, self.target.downcast().filesystem.mgs_id)

            deps.append(DependOn(mgs, "mounted"))

        if issubclass(self.target.downcast_class, ManagedOst):
            # FIXME: spurious downcast, should cache filesystem associaton in objectcache
            filesystem_id = self.target.downcast().filesystem_id
            mdts = ObjectCache.get(ManagedTarget, lambda target: issubclass(target.downcast_class,
                                                                            ManagedMdt) and target.downcast().filesystem_id == filesystem_id)

            for mdt in mdts:
                deps.append(DependOn(mdt, "mounted"))

        return DependAll(deps)


class MountStep(Step):
    idempotent = True

    def run(self, kwargs):
        target = kwargs['target']

        result = self.invoke_agent(kwargs['host'], "start_target", {'ha_label': target.ha_label})
        target.update_active_mount(result['location'])


class StartTargetJob(StateChangeJob):
    stateful_object = 'target'
    state_transition = (ManagedTarget, 'unmounted', 'mounted')
    state_verb = "Start"
    target = models.ForeignKey(ManagedTarget)

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    @classmethod
    def long_description(cls, stateful_object):
        return select_description(stateful_object, {ManagedOst: help_text["start_ost"],
                                                    ManagedMgs: help_text["start_mgt"],
                                                    ManagedMdt: help_text["start_mdt"]})

    def description(self):
        return "Start target %s" % self.target

    def get_deps(self):
        lnet_deps = []
        # Depend on at least one targetmount having lnet up
        mtms = ObjectCache.get(ManagedTargetMount, lambda mtm: mtm.target_id == self.target_id)
        for tm in mtms:
            host = ObjectCache.get_by_id(ManagedHost, tm.host_id)
            lnet_deps.append(DependOn(host, 'lnet_up', fix_state = 'unmounted'))
        return DependAny(lnet_deps)

    def get_steps(self):
        return [(MountStep, {"target": self.target, "host": self.target.best_available_host()})]


class UnmountStep(Step):
    idempotent = True

    def run(self, kwargs):
        target = kwargs['target']

        self.invoke_agent(kwargs['host'], "stop_target", {'ha_label': target.ha_label})
        target.active_mount = None


class StopTargetJob(StateChangeJob):
    stateful_object = 'target'
    state_transition = (ManagedTarget, 'mounted', 'unmounted')
    state_verb = "Stop"
    target = models.ForeignKey(ManagedTarget)

    def get_requires_confirmation(self):
        return True

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    @classmethod
    def long_description(cls, stateful_object):
        return select_description(stateful_object, {ManagedOst: help_text["stop_ost"],
                                                    ManagedMgs: help_text["stop_mgt"],
                                                    ManagedMdt: help_text["stop_mdt"]})

    def description(self):
        return "Stop target %s" % self.target

    def get_steps(self):
        return [(UnmountStep, {"target": self.target, "host": self.target.best_available_host()})]


class PreFormatCheck(Step):
    @classmethod
    def describe(cls, kwargs):
        return "Prepare for format %s:%s" % (kwargs['host'], kwargs['path'])

    def run(self, kwargs):
        occupying_fs = self.invoke_agent(kwargs['host'], "check_block_device", {'path': kwargs['path'],
                                                                                'device_type': kwargs['device_type']})
        if occupying_fs is not None:
            msg = "Found filesystem of type '%s' on %s:%s" % (occupying_fs, kwargs['host'], kwargs['path'])
            self.log(msg)
            raise RuntimeError(msg)


class PreFormatComplete(Step):
    """
    This step separated from PreFormatCheck so that it
    can write to the database without forcing the remote
    ops in the check to hold a DB connection (would limit
    parallelism).
    """
    database = True

    def run(self, kwargs):
        job_log.info("%s passed pre-format check, allowing subsequent reformats" % kwargs['target'])
        with transaction.commit_on_success():
            kwargs['target'].reformat = True
            kwargs['target'].save()


class MkfsStep(Step):
    def _mkfs_args(self, kwargs):
        target = kwargs['target']

        mkfs_args = {}

        mkfs_args['target_types'] = target.downcast().target_type()
        mkfs_args['target_name'] = target.name

        if issubclass(target.downcast_class, FilesystemMember):
            mkfs_args['fsname'] = target.downcast().filesystem.name
            mkfs_args['mgsnode'] = kwargs['mgs_nids']

        if kwargs['reformat']:
            mkfs_args['reformat'] = True

        if kwargs['failover_nids']:
            mkfs_args['failnode'] = kwargs['failover_nids']

        mkfs_args['device'] = kwargs['device_path']
        if issubclass(target.downcast_class, FilesystemMember):
            mkfs_args['index'] = target.downcast().index

        mkfs_args["device_type"] = kwargs['device_type']
        mkfs_args["backfstype"] = kwargs['backfstype']

        if len(kwargs['mkfsoptions']) > 0:
            mkfs_args['mkfsoptions'] = " ".join(kwargs['mkfsoptions'])

        return mkfs_args

    @classmethod
    def describe(cls, kwargs):
        target = kwargs['target']
        target_mount = target.managedtargetmount_set.get(primary = True)
        return "Format %s on %s" % (target, target_mount.host)

    def run(self, kwargs):
        target = kwargs['target']

        args = self._mkfs_args(kwargs)
        result = self.invoke_agent(kwargs['primary_host'], "format_target", args)

        if not (result['filesystem_type'] in FileSystem.all_supported_filesystems()):
            raise RuntimeError("Unexpected filesystem type '%s'" % result['filesystem_type'])

        # I don't think this should be here - seems kind of out of place - but I also don't see when else to store it.
        # See comment above about database = True
        target.volume.filesystem_type = result['filesystem_type']

        target.uuid = result['uuid']

        # Check that inode_size was applied correctly
        if target.inode_size:
            if target.inode_size != result['inode_size']:
                raise RuntimeError("Failed for format target with inode size %s, actual inode size %s" % (
                    target.inode_size, result['inode_size']))

        # Check that inode_count was applied correctly
        if target.inode_count:
            if target.inode_count != result['inode_count']:
                raise RuntimeError("Failed for format target with inode count %s, actual inode count %s" % (
                    target.inode_count, result['inode_count']))

        # NB cannot check that bytes_per_inode was applied correctly as that setting is not stored in the FS
        target.inode_count = result['inode_count']
        target.inode_size = result['inode_size']


class FormatTargetJob(StateChangeJob):
    state_transition = (ManagedTarget, 'unformatted', 'formatted')
    target = models.ForeignKey(ManagedTarget)
    stateful_object = 'target'
    state_verb = 'Format'
    cancellable = False

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    @classmethod
    def long_description(cls, stateful_object):
        return help_text['format_target']

    def description(self):
        return "Format %s" % self.target

    def get_deps(self):
        from chroma_core.models import ManagedFilesystem

        deps = []

        hosts = set()
        for tm in ObjectCache.get(ManagedTargetMount, lambda mtm: mtm.target_id == self.target_id):
            hosts.add(tm.host)

        for host in hosts:
            deps.append(DependOn(host, 'lnet_up'))

        if issubclass(self.target.downcast_class, FilesystemMember):
            # FIXME: spurious downcast, should use ObjectCache to remember which targets are in
            # which filesystem
            filesystem = ObjectCache.get_by_id(ManagedFilesystem, self.target.downcast().filesystem_id)
            mgt_id = filesystem.mgs_id

            mgs_hosts = set()
            for tm in ObjectCache.get(ManagedTargetMount, lambda mtm: mtm.target_id == mgt_id):
                mgs_hosts.add(tm.host)

            for host in mgs_hosts:
                deps.append(DependOn(host, 'lnet_up'))

        return DependAll(deps)

    def get_steps(self):
        primary_mount = self.target.managedtargetmount_set.get(primary = True)

        if issubclass(self.target.downcast_class, FilesystemMember):
            # FIXME: spurious downcast, should use ObjectCache to remember which targets are in
            # which filesystem
            mgs_nids = self.target.downcast().filesystem.mgs.nids()
        else:
            mgs_nids = None

        steps = []

        device_type = self.target.volume.storage_resource.to_resource_class().device_type()

        if not self.target.reformat:
            # We are not expecting to need to reformat/overwrite this volume
            # so before proceeding, check that it is indeed unoccupied
            steps.append((PreFormatCheck, {
                'host': primary_mount.host,
                'path': primary_mount.volume_node.path,
                'device_type': device_type
            }))

            steps.append((PreFormatComplete, {
                'target': self.target
            }))

        # This line is key, because it causes the volume property to be filled so it can be access by the step
        self.target.volume

        block_device = BlockDevice(device_type, primary_mount.volume_node.path)
        filesystem = FileSystem(block_device.preferred_fstype, primary_mount.volume_node.path)

        mkfsoptions = filesystem.mkfs_options(self.target)

        mkfsoptions = self.target.downcast().mkfs_override_options(block_device.preferred_fstype, mkfsoptions)

        steps.append((MkfsStep, {
            'primary_host': primary_mount.host,
            'target': self.target,
            'device_path': primary_mount.volume_node.path,
            'failover_nids': self.target.get_failover_nids(),
            'mgs_nids': mgs_nids,
            'reformat': self.target.reformat,
            'device_type': device_type,
            'backfstype': block_device.preferred_fstype,
            'mkfsoptions': mkfsoptions
       }))

        return steps

    def on_success(self):
        super(FormatTargetJob, self).on_success()
        self.target.volume.save()


class MigrateTargetJob(AdvertisedJob):
    target = models.ForeignKey(ManagedTarget)

    requires_confirmation = True

    classes = ['ManagedTarget']

    class Meta:
        abstract = True
        app_label = 'chroma_core'

    @classmethod
    def long_description(cls, stateful_object):
        return help_text['migrate_target']

    @classmethod
    def get_args(cls, target):
        return {'target_id': target.id}

    @classmethod
    def can_run(cls, instance):
        return False

    def create_locks(self):
        locks = super(MigrateTargetJob, self).create_locks()

        locks.append(StateLock(
            job = self,
            locked_item = self.target,
            begin_state = 'mounted',
            end_state = 'mounted',
            write = True
        ))

        return locks


class FailbackTargetStep(Step):
    idempotent = True

    def run(self, kwargs):
        target = kwargs['target']
        self.invoke_agent(kwargs['host'], "failback_target", {'ha_label': kwargs['target'].ha_label})
        target.active_mount = kwargs['primary_mount']


class FailbackTargetJob(MigrateTargetJob):
    verb = "Failback"

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    @classmethod
    def can_run(cls, instance):
        if instance.immutable_state:
            return False

        return len(instance.failover_hosts) > 0 and \
            instance.active_host is not None and\
            instance.primary_host != instance.active_host
        # HYD-1238: once we have a valid online/offline piece of info for each host,
        # reinstate the condition
        #instance.primary_host.is_available() and \

    @classmethod
    def long_description(cls, stateful_object):
        return help_text['failback_target']

    def description(self):
        FailbackTargetJob.long_description(None)

    def get_deps(self):
        return DependAll(
            [DependOn(self.target, 'mounted')] +
            [DependOn(self.target.primary_host, 'lnet_up')]
        )

    def on_success(self):
        # Persist the update to active_target_mount
        self.target.save()

    def get_steps(self):
        return [(FailbackTargetStep, {
            'target': self.target,
            'host': self.target.primary_host,
            'primary_mount': self.target.managedtargetmount_set.get(primary = True)
        })]

    @classmethod
    def get_confirmation(cls, instance):
        return """Migrate the target back to its primary server. Clients attempting to access data on the target while the migration is occurring may experience delays until the migration completes."""


class FailoverTargetStep(Step):
    idempotent = True

    def run(self, kwargs):
        target = kwargs['target']
        self.invoke_agent(kwargs['host'], "failover_target", {'ha_label': kwargs['target'].ha_label})
        target.active_mount = kwargs['secondary_mount']


class FailoverTargetJob(MigrateTargetJob):
    verb = "Failover"

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    @classmethod
    def can_run(cls, instance):
        if instance.immutable_state:
            return False

        return len(instance.failover_hosts) > 0 and\
            instance.primary_host == instance.active_host
    # HYD-1238: once we have a valid online/offline piece of info for each host,
    # reinstate the condition
#                instance.failover_hosts[0].is_available() and \

    @classmethod
    def long_description(cls, stateful_object):
        return help_text['failover_target']

    def description(self):
        FailoverTargetJob.long_description(None)

    def get_deps(self):
        return DependAll(
            [DependOn(self.target, 'mounted')] +
            [DependOn(self.target.failover_hosts[0], 'lnet_up')]
        )

    def on_success(self):
        # Persist the update to active_target_mount
        self.target.save()

    def get_steps(self):
        return [(FailoverTargetStep, {
            'target': self.target,
            'host': self.target.failover_hosts[0],
            'secondary_mount': self.target.managedtargetmount_set.get(primary = False)
        })]

    @classmethod
    def get_confirmation(cls, instance):
        return """Forcibly migrate the target to its failover server. Clients attempting to access data on the target while the migration is occurring may experience delays until the migration completes."""


class ManagedTargetMount(models.Model):
    """Associate a particular Lustre target with a device node on a host"""
    __metaclass__ = DeletableMetaclass

    # FIXME: both VolumeNode and TargetMount refer to the host
    host = models.ForeignKey('ManagedHost')
    mount_point = models.CharField(max_length = 512, null = True, blank = True)
    volume_node = models.ForeignKey('VolumeNode')
    primary = models.BooleanField()
    target = models.ForeignKey('ManagedTarget')

    def save(self, force_insert = False, force_update = False, using = None):
        # If primary is true, then target must be unique
        if self.primary:
            from django.db.models import Q
            other_primaries = ManagedTargetMount.objects.filter(~Q(id = self.id), target = self.target, primary = True)
            if other_primaries.count() > 0:
                from django.core.exceptions import ValidationError
                raise ValidationError("Cannot have multiple primary mounts for target %s" % self.target)

        # If this is an MGS, there may not be another MGS on
        # this host
        if issubclass(self.target.downcast_class, ManagedMgs):
            from django.db.models import Q
            other_mgs_mountables_local = ManagedTargetMount.objects.filter(~Q(id = self.id), target__in = ManagedMgs.objects.all(), host = self.host).count()
            if other_mgs_mountables_local > 0:
                from django.core.exceptions import ValidationError
                raise ValidationError("Cannot have multiple MGS mounts on host %s" % self.host.address)

        return super(ManagedTargetMount, self).save(force_insert, force_update, using)

    def device(self):
        return self.volume_node.path

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    def __str__(self):
        if self.primary:
            kind_string = "primary"
        elif not self.volume_node:
            kind_string = "failover_nodev"
        else:
            kind_string = "failover"

        return "%s:%s:%s" % (self.host, kind_string, self.target)


class TargetOfflineAlert(AlertState):
    # When a target is offline, some or all files in the filesystem are inaccessible,
    # therefore the filesystem is considered not fully available, therefore it's ERROR.
    default_severity = logging.ERROR

    def message(self):
        return "Target %s offline" % (self.alert_item)

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    def end_event(self):
        return AlertEvent(
            message_str = "%s started" % self.alert_item,
            host = self.alert_item.primary_server(),
            alert = self,
            severity = logging.INFO)


class TargetFailoverAlert(AlertState):
    # The filesystem should remain available while a target is failed over, but
    # performance may be degraded, therefore it's worse than INFO, but not as bad as ERROR.
    default_severity = logging.WARNING

    def message(self):
        return "Target %s running on secondary server" % self.alert_item

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    def end_event(self):
        return AlertEvent(
            message_str = "%s failover unmounted" % self.alert_item,
            host = self.alert_item.primary_server(),
            alert = self,
            severity = logging.INFO)


class TargetRecoveryAlert(AlertState):
    # While a target is in recovery, the filesystem is still available, but I/O operations
    # from clients may block until recovery completes, effectively degrading performance.
    # Therefore it's WARNING.
    default_severity = logging.WARNING

    def message(self):
        return "Target %s in recovery" % self.alert_item

    class Meta:
        app_label = 'chroma_core'
        ordering = ['id']

    def end_event(self):
        return AlertEvent(
            message_str = "Target '%s' completed recovery" % self.alert_item,
            host = self.alert_item.primary_server(),
            alert = self,
            severity = logging.INFO)
