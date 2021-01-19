# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


"""
WARNING:
    There is a global instance of ResourceManager initialized in this module, and
    its initialization does a significant amount of DB activity.  Don't import
    this module unless you're really going to use it.
"""
import logging
import json
import threading

from collections import defaultdict

from massiviu.context import DelayedContextFrom
from django.db.models.aggregates import Count
from django.db.models.query_utils import Q
from django.db import transaction

from chroma_core.lib.storage_plugin.api.resources import LogicalDrive, LogicalDriveSlice
from chroma_core.lib.storage_plugin.base_plugin import BaseStoragePlugin

from chroma_core.lib.storage_plugin.query import ResourceQuery

from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
from chroma_core.lib.storage_plugin.api import attributes, relations

from chroma_core.lib.storage_plugin.base_resource import (
    BaseGlobalId,
    BaseScopedId,
    HostsideResource,
    BaseScannableResource,
)
from chroma_core.lib.storage_plugin.base_resource import BaseStorageResource

from chroma_core.lib.storage_plugin.log import storage_plugin_log as log
from chroma_core.lib.util import all_subclasses

from chroma_core.models import ManagedHost, ManagedTarget
from chroma_core.models import LNetNidsChangedAlert
from chroma_core.models import Volume, VolumeNode
from chroma_core.models import StorageResourceRecord
from chroma_core.models import StorageResourceAlert, StorageResourceOffline
from chroma_core.models import HaCluster
from chroma_core.models.alert import AlertState
from chroma_core.models import LNetConfiguration, NetworkInterface, Nid

from chroma_core.models.storage_plugin import (
    StorageResourceAttributeSerialized,
    StorageResourceLearnEvent,
    StorageResourceAttributeReference,
    StorageAlertPropagated,
)


class PluginSession(object):
    def __init__(self, plugin_instance, scannable_id, update_period):
        # We have to be sure that this PluginSession is only associated with 1 single plugin_instance
        # otherwise the local<->global mappins don't work (among other possible issues) HYD-3068
        self._plugin_instance = plugin_instance
        self.local_id_to_global_id = {}
        self.global_id_to_local_id = {}
        self.scannable_id = scannable_id
        self.update_period = update_period


class EdgeIndex(object):
    def __init__(self):
        # Define: Edges go 'from' child 'to' parent
        # Map of 'from' to (from, to)
        self._parent_from_edge = defaultdict(set)
        # Map of 'to' to (from, to)
        self._parent_to_edge = defaultdict(set)

    def get_parents(self, child):
        return [e[1] for e in self._parent_from_edge[child]]

    def get_children(self, parent):
        return [e[0] for e in self._parent_to_edge[parent]]

    def add_parent(self, child, parent):
        edge = (child, parent)
        self._parent_from_edge[child].add(edge)
        self._parent_to_edge[parent].add(edge)

    def remove_parent(self, child, parent):
        edge = (child, parent)
        self._parent_from_edge[child].remove(edge)
        self._parent_to_edge[parent].remove(edge)

    def remove_node(self, node):
        edges = set()
        edges = edges | self._parent_from_edge[node]
        edges = edges | self._parent_to_edge[node]
        for e in edges:
            self.remove_parent(e[0], e[1])
        del self._parent_to_edge[node]
        del self._parent_from_edge[node]

    def populate(self):
        for srr in StorageResourceRecord.objects.filter(~Q(parents=None)).values("id", "parents"):
            child = srr["id"]
            parent = srr["parents"]
            self.add_parent(child, parent)


class ClassIndex(object):
    def __init__(self):
        self._record_id_to_class = {}

    def get(self, record_id):
        # For normal resources the value will always have been set during creation or in populate(),
        # but for root resources it may have been created in another process.
        try:
            result = self._record_id_to_class[record_id]
        except KeyError:
            result = StorageResourceRecord.objects.get(pk=record_id).resource_class.get_class()
            self._record_id_to_class[record_id] = result

        return result

    def add_record(self, record_id, record_class):
        self._record_id_to_class[record_id] = record_class

    def remove_record(self, record_id):
        try:
            del self._record_id_to_class[record_id]
        except KeyError:
            pass

    def populate(self):
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager

        for srr in StorageResourceRecord.objects.all().values("id", "resource_class_id"):
            self.add_record(srr["id"], storage_plugin_manager.get_resource_class_by_id(srr["resource_class_id"]))


class SubscriberIndex(object):
    def __init__(self):
        log.debug("SubscriberIndex.__init__")
        # Map (field_name, field_value) to list of resource global id
        self._subscribe_value_to_id = defaultdict(set)
        self._provide_value_to_id = defaultdict(set)

        # List of (provider, Provide object)
        self._all_subscriptions = []

        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager

        subscriptions = {}

        for id, klass in storage_plugin_manager.resource_class_id_to_class.items():
            klass._meta.subscriptions = []
            for relation in klass._meta.relations:
                if isinstance(relation, relations.Subscribe):
                    log.debug("klass = %s relation %s" % (klass, relation))
                    subscriptions[relation.key] = relation
                    klass._meta.subscriptions.append(relation)

        for id, klass in storage_plugin_manager.resource_class_id_to_class.items():
            if klass._meta.relations:
                log.debug("%s._meta.relations = %s" % (klass.__name__, klass._meta.relations))
            if klass._meta.subscriptions:
                log.debug("%s._meta.subscriptions = %s" % (klass.__name__, klass._meta.subscriptions))

        self._all_subscriptions = subscriptions.values()

    def what_provides(self, resource):
        """What provides things that this resource subscribes to?"""
        result = set()
        for subscription in resource._meta.subscriptions:
            result |= self._provide_value_to_id[(subscription.key, subscription.val(resource))]

        if result:
            log.debug("what_provides: %s" % result)

        return result

    def what_subscribes(self, resource):
        """What subscribes to this resources?"""
        result = set()
        for subscription in self._all_subscriptions:
            if isinstance(resource, subscription.subscribe_to):
                result |= self._subscribe_value_to_id[(subscription.key, subscription.val(resource))]

        if result:
            log.debug("what_subscribes: %s" % result)
        return result

    def add_provider(self, resource_id, key, value):
        self._provide_value_to_id[(key, value)].add(resource_id)

    def remove_provider(self, resource_id, key, value):
        self._provide_value_to_id[(key, value)].remove(resource_id)

    def add_subscriber(self, resource_id, key, value):
        log.debug("add_subscriber %s %s %s" % (resource_id, key, value))
        self._subscribe_value_to_id[(key, value)].add(resource_id)

    def remove_subscriber(self, resource_id, key, value):
        log.debug("remove_subscriber %s %s %s" % (resource_id, key, value))
        self._subscribe_value_to_id[(key, value)].remove(resource_id)

    def add_resource(self, resource_id, resource):
        for subscription in self._all_subscriptions:
            if isinstance(resource, subscription.subscribe_to):
                self.add_provider(resource_id, subscription.key, subscription.val(resource))
        for subscription in resource._meta.subscriptions:
            self.add_subscriber(resource_id, subscription.key, subscription.val(resource))

    def remove_resource(self, resource_id, resource_class):
        log.debug("SubscriberIndex.remove_resource %s %s" % (resource_class, resource_id))

        for subscription in self._all_subscriptions:
            if issubclass(resource_class, subscription.subscribe_to):
                # FIXME: performance: only load the attr we need instead of whole resource
                resource = StorageResourceRecord.objects.get(pk=resource_id).to_resource()
                log.debug("SubscriberIndex.remove provider %s" % subscription.key)
                self.remove_provider(resource_id, subscription.key, subscription.val(resource))
        log.debug("subscriptions = %s" % resource_class._meta.subscriptions)
        for subscription in resource_class._meta.subscriptions:
            # FIXME: performance: only load the attr we need instead of whole resource
            resource = StorageResourceRecord.objects.get(pk=resource_id).to_resource()
            log.debug("SubscriberIndex.remove subscriber %s" % subscription.key)
            self.remove_subscriber(resource_id, subscription.key, subscription.val(resource))

    def populate(self):
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager

        for resource_class_id, resource_class in storage_plugin_manager.get_all_resources():
            for subscription in self._all_subscriptions:
                if issubclass(resource_class, subscription.subscribe_to):
                    records = StorageResourceRecord.objects.filter(resource_class=resource_class_id)
                    for r in records:
                        resource = r.to_resource()
                        self.add_provider(r.id, subscription.key, subscription.val(resource))

            for subscription in resource_class._meta.subscriptions:
                records = StorageResourceRecord.objects.filter(resource_class=resource_class_id)
                for r in records:
                    resource = r.to_resource()
                    self.add_subscriber(r.id, subscription.key, subscription.val(resource))


class ResourceManager(object):
    """The resource manager is the home of the global view of the resources populated from
    all plugins.  BaseStoragePlugin instances have their own local caches of resources, which
    they use to periodically update this central store.

    Acts as a pseudo-database layer on top of the underlying (StorageResourceRecord et al)
    models.  Tracks which resources are reported by which ScannableResources, acts on relationship
    rules to hook resources with matching IDs together, creates Volumes and VolumeNodes for reported
    LUNs, creates ManagedHost objects for reported VMs.

    BaseStoragePlugin subclass instances maintain local copies of the resources that their callbacks
    create with update_or_create, and then report those copies within their ResourceManager session.
    ResourceManager resolves identical resources reported by more than one plugin instance (e.g. LUNs
    seen from more than one location) and creates a globally unique record corresponding to the local
    instance that the BaseStoragePlugin has in memory.  Sessions have a local_id_to_global_id map
    which records that relation: entry points to ResourceManager map the BaseStoragePlugin (local) ID
    to the ResourceManager (global) ID.

    This class is a performance hot-spot because it is contended by multiple hosts and controllers and
    potentially acts on large numbers of objects (e.g. thousands of hard drives), so be careful to phrase
    your database queries efficiently.

    This code is written for multi-threaded use within a single process.
    It is not safe to have multiple processes running plugins at this stage.
    We serialize operations from different plugins using a big lock, and
    we use the autocommit decorator on persistence functions because
    otherwise we would have to explicitly commit at the start of
    each one to see changes from other threads.

    """

    def __init__(self):
        self._sessions = {}
        self._instance_lock = threading.Lock()

        # Map of (resource_global_id, alert_class) to AlertState pk
        self._active_alerts = {}

        # In-memory bidirectional lookup table of resource parent-child relationships
        self._edges = EdgeIndex()
        self._edges.populate()

        self._class_index = ClassIndex()
        self._class_index.populate()

        # In-memory lookup table of 'provide' and 'subscribe' resource attributes
        self._subscriber_index = SubscriberIndex()
        self._subscriber_index.populate()

        self._label_cache = {}

    def session_open(self, plugin_instance, scannable_id, initial_resources, update_period):

        # Assert the types, they are not optional or duckable
        assert isinstance(plugin_instance, BaseStoragePlugin)
        assert isinstance(scannable_id, int)
        assert isinstance(initial_resources, list)
        assert isinstance(update_period, int)

        scannable_class = self._class_index.get(scannable_id)
        assert issubclass(scannable_class, BaseScannableResource) or issubclass(scannable_class, HostsideResource)
        log.debug(">> session_open %s (%s resources)" % (scannable_id, len(initial_resources)))
        with self._instance_lock:
            if scannable_id in self._sessions:
                log.warning("Clearing out old session for scannable ID %s" % scannable_id)
                del self._sessions[scannable_id]

            session = PluginSession(plugin_instance, scannable_id, update_period)

            try:
                # If this returns a BaseStorageResource such as
                # PluginAgentResources, with a host_id
                # set it in the session for later use.
                resource = ResourceQuery().get_resource(session.scannable_id)
                if resource and hasattr(resource, "host_id"):
                    session.host_id = resource.host_id
            except BaseStorageResource.DoesNotExist:
                pass

            self._sessions[scannable_id] = session

            with transaction.atomic():
                self._persist_new_resources(session, initial_resources)
                self._cull_lost_resources(session, initial_resources)

                self._persist_lun_updates(scannable_id)
                self._persist_nid_updates(scannable_id, None, None)

                # Plugins are allowed to create VirtualMachine objects, indicating that
                # we should created a ManagedHost to go with it (e.g. discovering VMs)
                self._persist_created_hosts(session, scannable_id, initial_resources)

        log.debug("<< session_open %s" % scannable_id)

    def session_close(self, scannable_id):
        with self._instance_lock:
            try:
                del self._sessions[scannable_id]
            except KeyError:
                log.warning("Cannot remove session for %s, it does not exist" % scannable_id)

    def _persist_created_hosts(self, session, scannable_id, new_resources):
        # Must be run in a transaction to avoid leaving invalid things in the DB on failure.
        assert not transaction.get_autocommit()

        log.debug("_persist_created_hosts")

        record_pks = []
        from chroma_core.lib.storage_plugin.api.resources import VirtualMachine

        for resource in new_resources:
            if isinstance(resource, VirtualMachine):
                assert not resource._handle_global
                record_pks.append(session.local_id_to_global_id[resource._handle])

        for vm_record_pk in record_pks:
            record = StorageResourceRecord.objects.get(pk=vm_record_pk)
            resource = record.to_resource()

            if not resource.host_id:
                try:
                    host = ManagedHost.objects.get(address=resource.address)
                    log.info("Associated existing host with VirtualMachine resource: %s" % resource.address)
                    record.update_attribute("host_id", host.pk)
                except ManagedHost.DoesNotExist:
                    log.info("Creating host for new VirtualMachine resource: %s" % resource.address)
                    host, command = JobSchedulerClient.create_host_ssh(resource.address)
                    record.update_attribute("host_id", host.pk)

    def get_label(self, record_id):
        try:
            if (
                StorageResourceRecord.objects.get(pk=record_id).to_resource().get_label()
                != self._label_cache[record_id]
            ):
                pass

            return self._label_cache[record_id]
        except KeyError:
            return StorageResourceRecord.objects.get(pk=record_id).to_resource().get_label()

    def _persist_lun_updates(self, scannable_id):
        from chroma_core.lib.storage_plugin.query import ResourceQuery
        from chroma_core.lib.storage_plugin.api.resources import DeviceNode, LogicalDriveOccupier
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager
        from chroma_core.lib.storage_plugin.base_resource import HostsideResource

        # Must be run in a transaction to avoid leaving invalid things in the DB on failure.
        assert not transaction.get_autocommit()

        scannable_resource = ResourceQuery().get_resource(scannable_id)

        if not isinstance(scannable_resource, HostsideResource):
            return
        else:
            log.debug("_persist_lun_updates for scope record %s" % scannable_id)
            host = ManagedHost.objects.get(pk=scannable_resource.host_id)

        # Get all DeviceNodes on this host
        node_klass_ids = [storage_plugin_manager.get_resource_class_id(klass) for klass in all_subclasses(DeviceNode)]

        node_resources = StorageResourceRecord.objects.filter(
            resource_class__in=node_klass_ids, storage_id_scope=scannable_id
        ).annotate(child_count=Count("resource_parent"))

        # DeviceNodes eligible for use as a VolumeNode (leaves)
        usable_node_resources = [nr for nr in node_resources if nr.child_count == 0]

        # DeviceNodes which are usable but don't have VolumeNode
        assigned_resource_ids = [
            ln["storage_resource_id"]
            for ln in VolumeNode.objects.filter(storage_resource__in=[n.id for n in node_resources]).values(
                "id", "storage_resource_id"
            )
        ]
        unassigned_node_resources = [nr for nr in usable_node_resources if nr.id not in assigned_resource_ids]

        # VolumeNodes whose storage resource is within this scope
        scope_volume_nodes = VolumeNode.objects.filter(storage_resource__storage_id_scope=scannable_id)

        log.debug(
            "%s %s %s %s"
            % (
                tuple(
                    [
                        len(l)
                        for l in [node_resources, usable_node_resources, unassigned_node_resources, scope_volume_nodes]
                    ]
                )
            )
        )

        # For all unattached DeviceNode resources, find or create VolumeNodes
        volumes_for_affinity_checks = set()
        node_to_logicaldrive_id = {}
        for node_record in unassigned_node_resources:
            logicaldrive_id = self._record_find_ancestor(node_record.id, LogicalDrive)
            if logicaldrive_id == None:
                # This is not an error: a plugin may report a device node from
                # an agent plugin before reporting the LogicalDrive from the controller.
                log.info("DeviceNode %s has no LogicalDrive ancestor" % node_record.pk)
                continue
            else:
                node_to_logicaldrive_id[node_record] = logicaldrive_id

        # Get the sizes, filesystem_type and device_type for all of the logicaldrive resources
        logicaldrive_id_to_attribute = defaultdict(dict)

        for resource in StorageResourceRecord.objects.filter(id__in=node_to_logicaldrive_id.values()):
            for attribute_name in ["size", "filesystem_type", "usable_for_lustre"]:
                attribute_value = getattr(resource.to_resource(), attribute_name)
                logicaldrive_id_to_attribute[attribute_name][resource.id] = attribute_value

        existing_volumes = Volume.objects.filter(storage_resource__in=node_to_logicaldrive_id.values())
        logicaldrive_id_to_volume = dict([(v.storage_resource_id, v) for v in existing_volumes])
        logicaldrive_id_handled = set()

        with DelayedContextFrom(Volume) as volumes:
            for _, logicaldrive_id in node_to_logicaldrive_id.items():
                if logicaldrive_id not in logicaldrive_id_to_volume and logicaldrive_id not in logicaldrive_id_handled:
                    # If this logicaldrive has one and only one ancestor which is
                    # also a logicaldrive, then inherit the label from that ancestor
                    ancestors = self._record_find_ancestors(logicaldrive_id, LogicalDrive)
                    record_class = self._class_index.get(logicaldrive_id)
                    ancestors.remove(logicaldrive_id)

                    if (
                        len(ancestors) == 1
                        and not issubclass(record_class, LogicalDriveSlice)
                        and not issubclass(self._class_index.get(ancestors[0]), LogicalDriveSlice)
                    ):
                        label = self.get_label(ancestors[0])
                    else:
                        label = self.get_label(logicaldrive_id)

                    # Check if there are any descendent LocalMount resources (i.e. LUN in use, do
                    # not advertise for use with Lustre).
                    if self._record_find_descendent(logicaldrive_id, LogicalDriveOccupier, LogicalDrive):
                        log.debug("LogicalDrive %s is occupied, not creating Volume" % logicaldrive_id)
                        logicaldrive_id_handled.add(logicaldrive_id)
                        for nr in [
                            node_record
                            for (node_record, ld_id) in node_to_logicaldrive_id.items()
                            if ld_id == logicaldrive_id
                        ]:
                            unassigned_node_resources.remove(nr)
                            del node_to_logicaldrive_id[nr]
                        continue

                    volumes.insert(
                        dict(
                            size=logicaldrive_id_to_attribute["size"][logicaldrive_id],
                            filesystem_type=logicaldrive_id_to_attribute["filesystem_type"][logicaldrive_id],
                            storage_resource_id=logicaldrive_id,
                            usable_for_lustre=logicaldrive_id_to_attribute["usable_for_lustre"][logicaldrive_id],
                            not_deleted=True,
                            label=label,
                        )
                    )
                    logicaldrive_id_handled.add(logicaldrive_id)

        existing_volumes = Volume.objects.filter(storage_resource__in=node_to_logicaldrive_id.values())
        logicaldrive_id_to_volume = dict([(v.storage_resource_id, v) for v in existing_volumes])

        path_attrs = StorageResourceAttributeSerialized.objects.filter(
            key="path", resource__in=unassigned_node_resources
        ).values("resource_id", "value")
        node_record_id_to_path = dict(
            [(p["resource_id"], StorageResourceAttributeSerialized.decode(p["value"])) for p in path_attrs]
        )

        existing_volume_nodes = VolumeNode.objects.filter(host=host, path__in=node_record_id_to_path.values())
        path_to_volumenode = dict([(vn.path, vn) for vn in existing_volume_nodes])

        # Find any nodes which refer to the same logicaldrive
        # on the same host: we will want to create only one
        # VolumeNode per host per Volume if possible.
        logicaldrive_id_to_nodes = defaultdict(list)
        for node_record in unassigned_node_resources:
            logicaldrive_id_to_nodes[node_to_logicaldrive_id[node_record]].append(node_record)

        for ld_id, nr_list in logicaldrive_id_to_nodes.items():
            if ld_id in logicaldrive_id_to_volume:
                volume_nodes = VolumeNode.objects.filter(volume=logicaldrive_id_to_volume[ld_id])
                for vn in volume_nodes:
                    if vn.storage_resource_id:
                        nr_list.append(StorageResourceRecord.objects.get(pk=vn.storage_resource_id))

        for ld_id, nr_list in [(ld_id, nr) for ld_id, nr in logicaldrive_id_to_nodes.items() if len(nr) > 1]:
            # If one and only one of the nodes is a devicemapper node, prefer it over the others.
            dm_node_ids = []
            node_id_to_path = {}
            for attr in StorageResourceAttributeSerialized.objects.filter(resource__in=nr_list, key="path"):
                path = attr.decode(attr.value)
                node_id_to_path[attr.resource_id] = path
                if path.startswith("/dev/mapper/"):
                    dm_node_ids.append(attr.resource_id)
            if len(dm_node_ids) == 1:
                log.debug("Found one devicemapper node %s" % node_id_to_path[dm_node_ids[0]])
                preferred_node_id = dm_node_ids[0]
                for nr in nr_list:
                    if nr.id != preferred_node_id:
                        try:
                            unassigned_node_resources.remove(nr)
                        except ValueError:
                            # Doesn't have to be in unassigned_node_resources, could be a pre-existing one
                            pass

                        try:
                            self._remove_volume_node(VolumeNode.objects.get(storage_resource=nr), False)
                        except VolumeNode.DoesNotExist:
                            pass
            else:
                log.debug(
                    "Cannot resolve %d nodes %s into one (logicaldrive id %s)"
                    % (len(nr_list), [node_id_to_path.items()], ld_id)
                )

        with DelayedContextFrom(VolumeNode) as volume_nodes:
            for node_record in unassigned_node_resources:
                volume = logicaldrive_id_to_volume[node_to_logicaldrive_id[node_record]]
                log.info("Setting up DeviceNode %s" % node_record.pk)
                path = node_record_id_to_path[node_record.id]

                if path not in path_to_volumenode:
                    volume_nodes.insert(
                        dict(
                            volume_id=volume.id,
                            host_id=host.id,
                            path=path,
                            storage_resource_id=node_record.pk,
                            primary=False,
                            use=False,
                            not_deleted=True,
                        )
                    )

                log.info("Created VolumeNode for resource %s" % node_record.pk)
                volumes_for_affinity_checks.add(volume)

        volume_to_volume_nodes = defaultdict(list)
        for vn in VolumeNode.objects.filter(volume__in=volumes_for_affinity_checks):
            volume_to_volume_nodes[vn.volume_id].append(vn)

        # For all VolumeNodes, if its storage resource was in this scope, and it
        # was not included in the set of usable DeviceNode resources, remove
        # the VolumeNode
        usable_node_resource_ids = [nr.id for nr in usable_node_resources]
        for volume_node in scope_volume_nodes:
            log.debug(
                "volume node %s (%s) usable %s"
                % (
                    volume_node.id,
                    volume_node.storage_resource_id,
                    volume_node.storage_resource_id in usable_node_resource_ids,
                )
            )
            if volume_node.storage_resource_id not in usable_node_resource_ids:
                self._remove_volume_node(volume_node, True)

    def _try_removing_volume(self, volume):
        nodes = VolumeNode.objects.filter(volume=volume)

        if nodes.count() == 0:
            log.info("Removing Volume %s" % volume.id)
            volume.storage_resource = None
            volume.save()
            volume.mark_deleted()
            return True
        else:
            log.warn("Leaving Volume %s, used by nodes %s" % (volume.id, [n.id for n in nodes]))
            return False

    def _remove_volume_node(self, volume_node, try_remove_volume):
        log.info("Removing VolumeNode %s" % volume_node.id)
        volume_node.storage_resource = None
        volume_node.save()
        volume_node.mark_deleted()

        if try_remove_volume:
            self._try_removing_volume(volume_node.volume)

    # Fixme: This function that should just not be in resource_manager will leave just looking at networks
    def _delete_nid_resource(self, scannable_id, deleted_resource_id):
        from chroma_core.lib.storage_plugin.api.resources import LNETInterface, NetworkInterface as SrcNetworkInterface

        resource = StorageResourceRecord.objects.get(pk=deleted_resource_id).to_resource()

        # Must be run in a transaction to avoid leaving invalid things in the DB on failure.
        assert not transaction.get_autocommit()

        # Shame to do this twice, but it seems that the scannable resource might not always be a host
        # according to this test_subscriber
        # But we will presume only a host can have a NetworkInterface or an LNetInterface
        if isinstance(resource, SrcNetworkInterface) or isinstance(resource, LNETInterface):
            scannable_resource = ResourceQuery().get_resource(scannable_id)
            host = ManagedHost.objects.get(pk=scannable_resource.host_id)

            if isinstance(resource, SrcNetworkInterface):
                log.error("Deleting NetworkInterface %s from %s" % (resource.name, host.fqdn))
                NetworkInterface.objects.filter(host=host, name=resource.name).delete()
            elif isinstance(resource, LNETInterface):
                log.error("Deleting Nid %s from %s" % (resource.name, host.fqdn))
                network_interface = NetworkInterface.objects.get(
                    host=host, name=resource.name
                )  # Presumes Nid name == Interface Name, that is asserted when it is added!yes
                Nid.objects.filter(network_interface=network_interface).delete()

    def _persist_nid_updates(self, scannable_id, changed_resource_id, changed_attrs):
        from chroma_core.lib.storage_plugin.api.resources import (
            LNETInterface,
            LNETModules,
            NetworkInterface as SrcNetworkInterface,
        )
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager

        # Must be run in a transaction to avoid leaving invalid things in the DB on failure.
        assert not transaction.get_autocommit()

        scannable_resource = ResourceQuery().get_resource(scannable_id)

        # Fixme: This is a bit of rubbish where this routine gets called when it should. Heh you should have called
        # me so I'll exit. Functions that anticipate the requirements by knowing the caller a seriously flawed.
        if not isinstance(scannable_resource, HostsideResource):
            return
        else:
            log.debug("_persist_nid_updates for scope record %s" % scannable_id)
            host = ManagedHost.objects.get(pk=scannable_resource.host_id)

        # We want to raise an alert if the nid configuration changes. So remember it at the start.
        previous_nids = host.lnet_configuration.get_nids()

        node_resources = {}

        for resource_klass in [LNETInterface, LNETModules, SrcNetworkInterface]:
            # Get all classes on this host
            node_klass_ids = [
                storage_plugin_manager.get_resource_class_id(klass) for klass in all_subclasses(resource_klass)
            ]

            # Now get all the node resources for that scannable_id (Host)
            node_resources[resource_klass] = StorageResourceRecord.objects.filter(
                resource_class__in=node_klass_ids, storage_id_scope=scannable_id
            ).annotate(child_count=Count("resource_parent"))

        nw_interfaces = {}

        for nw_resource in node_resources[SrcNetworkInterface]:
            nw_resource = nw_resource.to_resource()

            if nw_resource.host_id == host.id:
                try:
                    nw_interface = NetworkInterface.objects.get(host=host, name=nw_resource.name)
                except NetworkInterface.DoesNotExist:
                    nw_interface = NetworkInterface.objects.create(
                        host=host, name=nw_resource.name, inet4_prefix=nw_resource.inet4_prefix
                    )

                if (
                    nw_interface.inet4_address != nw_resource.inet4_address
                    or nw_interface.inet4_prefix != nw_resource.inet4_prefix
                    or nw_interface.type != nw_resource.type
                    or nw_interface.state_up != nw_resource.up
                ):
                    nw_interface.inet4_address = nw_resource.inet4_address
                    nw_interface.inet4_prefix = nw_resource.inet4_prefix
                    nw_interface.type = nw_resource.type
                    nw_interface.state_up = nw_resource.up
                    nw_interface.save()

                    log.debug("_persist_nid_updates nw_resource %s" % nw_interface)

                nw_interfaces[nw_resource._handle] = nw_interface

        for lnet_state_resource in node_resources[LNETModules]:
            lnet_state = lnet_state_resource.to_resource()

            # Really this code should be more tightly tied to the lnet_configuration classes, but in a one step
            # at a time approach. Until lnet is !unconfigured we should not be updating it's state.
            # Double if because the first if should be removed really, in some more perfect future.
            if host.lnet_configuration.state != "unconfigured":
                if lnet_state.host_id == host.id:
                    lnet_configuration = LNetConfiguration.objects.get(host=lnet_state.host_id)

                    # Truthfully this should use the notify which I've added as a comment to show the correct way. The problem is that
                    # during the ConfigureLNetJob the state is changed to unloaded and this masks the notify in some way the is probably
                    # as planned but prevents it being set back. What we really need is to somehow get a single command that goes
                    # to a state and then to another state. post_dependencies almost. At present I can't see how to do this so I am leaving
                    # this code as is.
                    lnet_configuration.set_state(lnet_state.state)
                    lnet_configuration.save()
                    # JobSchedulerClient.notify(lnet_configuration, now(), {'state': lnet_state.state})

                    log.debug("_persist_nid_updates lnet_configuration %s" % lnet_configuration)

        # Only get the lnet_configuration if we actually have a LNetInterface (nid) to add.
        if len(node_resources[LNETInterface]) > 0:
            # So get all the Nid's for this host, we will have to expand this to do network cards but
            # one step at a time.
            lnet_configuration = LNetConfiguration.objects.get(host=host)

            for nid_resource in node_resources[LNETInterface]:
                source_nid = nid_resource.to_resource()
                parent = self._record_find_ancestor(nid_resource.id, SrcNetworkInterface)

                # This is checking if this nid is on this host.
                if parent in nw_interfaces:
                    nid, created = Nid.objects.get_or_create(
                        lnet_configuration=lnet_configuration, network_interface=nw_interfaces[parent]
                    )

                    if nid.lnd_network != source_nid.lnd_network or nid.lnd_type != source_nid.lnd_type:
                        nid.lnd_network = source_nid.lnd_network
                        nid.lnd_type = source_nid.lnd_type
                        nid.save()

                        log.debug("_persist_nid_updates nid %s %s" % (nid, "created" if created else "updated"))

        # We want to raise an alert if the nid configuration changes. So check it at the end.
        if previous_nids != []:
            new_nids = host.lnet_configuration.get_nids()
            current = set(previous_nids) == set(new_nids)
            LNetNidsChangedAlert.notify(host, not current)

    def session_update_resource(self, scannable_id, record_id, attrs):
        """
        This is a first pass implementation by Chris, not really sure what this is trying to do but I
        need a solution to deal with lnet configuration including nids changing. So don't rely on this
        as the way to do it, just a way do do it.

        This implementation is really so sub optimal at the moment it is untrue, because it gets called
        for every field that changes for every record. I may change this comment if I can work out a solution!
        """
        with self._instance_lock:
            with transaction.atomic():
                self._resource_persist_update_attributes(scannable_id, record_id, attrs)
                # self._persist_lun_updates(scannable_id)
                self._persist_nid_updates(scannable_id, record_id, attrs)
                # self._persist_created_hosts(scannable_id, scannable_id, resources)

    def session_resource_add_parent(self, scannable_id, local_resource_id, local_parent_id):

        with self._instance_lock:
            session = self._sessions[scannable_id]
            record_pk = session.local_id_to_global_id[local_resource_id]

            # HYD-6845 Test failure: RpcError - missing parent resource
            # This is the worst kind of hack, no excuses but short of not delivering the the product this
            # is the best we can come up with. It is possibly an ordering thing that the parent has not been
            # created at the point the child is created, possibly something else.
            # If the former then we believe that the code will on the next update have the parent and so update
            # the child. If not then items in the tree view may show items as leafs that are actually branches and
            # give the user an option they should not use. For example left them select a disk when it has a partition
            # Only time will tell but if this patch landed and you are reading this then we never came up with a proper
            # solution in the time available.
            try:
                parent_pk = session.local_id_to_global_id[local_parent_id]
            except KeyError:
                return

            self._edges.add_parent(record_pk, parent_pk)
            self._resource_modify_parent(record_pk, parent_pk, False)

    def session_resource_remove_parent(self, scannable_id, local_resource_id, local_parent_id):
        with self._instance_lock:
            session = self._sessions[scannable_id]
            record_pk = session.local_id_to_global_id[local_resource_id]
            parent_pk = session.local_id_to_global_id[local_parent_id]
            self._edges.remove_parent(record_pk, parent_pk)
            self._resource_modify_parent(record_pk, parent_pk, True)

    def _resource_modify_parent(self, record_pk, parent_pk, remove):
        record = StorageResourceRecord.objects.get(pk=record_pk)
        if remove:
            record.parents.remove(parent_pk)
        else:
            record.parents.add(parent_pk)

    def _resource_persist_update_attributes(self, scannable_id, local_record_id, attrs):
        session = self._sessions[scannable_id]

        global_record_id = session.local_id_to_global_id[local_record_id]

        record = StorageResourceRecord.objects.get(pk=global_record_id)

        """ Sometimes we are given reference to a BaseStorageResource and so we need to store the id
            not the type. This code does the translation """
        cleaned_id_attrs = {}
        for key, val in attrs.items():
            if isinstance(val, BaseStorageResource):
                cleaned_id_attrs[key] = session.local_id_to_global_id[val._handle]
            else:
                cleaned_id_attrs[key] = val

        record.update_attributes(cleaned_id_attrs)

    def session_add_resources(self, scannable_id, resources):
        """NB this is plural because new resources may be interdependent
        and if so they must be added in a blob so that we can hook up the
        parent relationships"""

        with self._instance_lock:
            session = self._sessions[scannable_id]

            with transaction.atomic():
                self._persist_new_resources(session, resources)
                self._persist_lun_updates(scannable_id)
                self._persist_nid_updates(scannable_id, None, None)
                self._persist_created_hosts(session, scannable_id, resources)

    def session_remove_local_resources(self, scannable_id, resources):
        with self._instance_lock:
            session = self._sessions[scannable_id]

            with transaction.atomic():
                for local_resource in resources:
                    try:
                        resource_global_id = session.local_id_to_global_id[local_resource._handle]
                        self._delete_nid_resource(scannable_id, resource_global_id)
                        self._delete_resource(StorageResourceRecord.objects.get(pk=resource_global_id))
                    except KeyError:
                        pass
                self._persist_lun_updates(scannable_id)

    def session_remove_global_resources(self, scannable_id, resources):
        with self._instance_lock:
            session = self._sessions[scannable_id]
            resources = session._plugin_instance._index._local_id_to_resource.values()

            with transaction.atomic():
                self._cull_lost_resources(session, resources)
                self._persist_lun_updates(scannable_id)

    def session_notify_alert(self, scannable_id, resource_local_id, active, severity, alert_class, attribute):
        with self._instance_lock:
            session = self._sessions[scannable_id]
            record_pk = session.local_id_to_global_id[resource_local_id]
            if active:
                if not (record_pk, alert_class) in self._active_alerts:
                    alert_state = self._persist_alert(record_pk, active, severity, alert_class, attribute)
                    if alert_state:
                        self._persist_alert_propagate(alert_state)
                        self._active_alerts[(record_pk, alert_class)] = alert_state.pk
            else:
                alert_state = self._persist_alert(record_pk, active, severity, alert_class, attribute)
                if alert_state:
                    self._persist_alert_unpropagate(alert_state)
                if (record_pk, alert_class) in self._active_alerts:
                    del self._active_alerts[(record_pk, alert_class)]

    def _get_descendents(self, record_global_pk):
        def collect_children(resource_id):
            result = set()
            child_record_ids = self._edges.get_children(resource_id)
            result = result | set(child_record_ids)
            for c in child_record_ids:
                result = result | collect_children(c)
            return result

        return list(collect_children(record_global_pk))

    # FIXME: the alert propagation and unpropagation should happen with the AlertState
    # raise/lower in a transaction.
    def _persist_alert_propagate(self, alert_state):
        record_global_pk = alert_state.alert_item_id
        descendents = self._get_descendents(record_global_pk)
        for d in descendents:
            sap, created = StorageAlertPropagated.objects.get_or_create(storage_resource_id=d, alert_state=alert_state)

    def _persist_alert_unpropagate(self, alert_state):
        StorageAlertPropagated.objects.filter(alert_state=alert_state).delete()

    # If we _persist_alert down, then lose power, we will forget all about the alert
    # before we remove the PropagatedAlerts for it: actually need to do a two step
    # removal where we check if there's something there, and if there is then we
    # remove the propagated alerts, and then finally mark inactive the alert itself.
    def _persist_alert(self, record_pk, active, severity, alert_class, attribute):
        assert isinstance(alert_class, str)
        record = StorageResourceRecord.objects.get(pk=record_pk)
        alert_state = StorageResourceAlert.notify(
            record,
            active,
            alert_class=alert_class,
            attribute=attribute,
            severity=severity,
            alert_type="StorageResourceAlert_%s" % alert_class,
        )
        return alert_state

    def _cull_lost_resources(self, session, reported_resources):
        # Must be run in a transaction to avoid leaving invalid things in the DB on failure.
        assert not transaction.get_autocommit()

        reported_scoped_resources = []
        reported_global_resources = []
        for r in reported_resources:
            try:
                if isinstance(r._meta.identifier, BaseScopedId):
                    reported_scoped_resources.append(session.local_id_to_global_id[r._handle])
                else:
                    reported_global_resources.append(session.local_id_to_global_id[r._handle])
            except KeyError as e:
                log.warning("attempting to access resource missing from local-global map {}".format(e))

        # This generator re-runs the query on every loop iteration in order
        # to handle situations where resources returned by the query are
        # deleted as dependents of prior resources (HYD-3659).
        def iterate_lost_resources(query):
            loops_remaining = len(query())
            while loops_remaining:
                loops_remaining -= 1
                rs = query()
                if len(rs):
                    yield rs[0]
                else:
                    raise StopIteration()

            # If the list of lost items grew, don't continue looping.
            # Just bail out and the next scan will get them.
            if loops_remaining <= 0:
                raise StopIteration()

        # Look for scoped resources which were at some point reported by
        # this scannable_id, but are missing this time around.
        lost_scoped_resources = lambda: StorageResourceRecord.objects.filter(
            ~Q(pk__in=reported_scoped_resources), storage_id_scope=session.scannable_id
        )
        for r in iterate_lost_resources(lost_scoped_resources):
            self._delete_resource(r)

        # Look for globalid resources which were at some point reported by
        # this scannable_id, but are missing this time around.
        lost_global_resources = lambda: StorageResourceRecord.objects.filter(
            ~Q(pk__in=reported_global_resources), reported_by=session.scannable_id
        )
        for reportee in iterate_lost_resources(lost_global_resources):
            reportee.reported_by.remove(session.scannable_id)
            if not reportee.reported_by.count():
                self._delete_resource(reportee)

    def _delete_resource(self, resource_record):
        log.info("ResourceManager._delete_resource '%s'" % resource_record.pk)

        ordered_for_deletion = []
        phase1_ordered_dependencies = []

        def collect_phase1(record_id):
            if not record_id in phase1_ordered_dependencies:
                phase1_ordered_dependencies.append(record_id)

        # If we are deleting one of the special top level resource classes, handle
        # its dependents
        record_id = resource_record.id
        from chroma_core.lib.storage_plugin.base_resource import BaseScannableResource, HostsideResource

        resource_class = self._class_index.get(record_id)
        if issubclass(resource_class, BaseScannableResource) or issubclass(resource_class, HostsideResource):
            # Find resources scoped to this resource
            for dependent in StorageResourceRecord.objects.filter(storage_id_scope=record_id):
                collect_phase1(dependent.id)

            # Delete any reported_by relations to this resource
            StorageResourceRecord.reported_by.through._default_manager.filter(
                **{"%s" % StorageResourceRecord.reported_by.field.m2m_reverse_field_name(): record_id}
            ).delete()

            # Delete any resources whose reported_by are now zero
            for srr in StorageResourceRecord.objects.filter(storage_id_scope=None, reported_by=None).values("id"):
                srr_class = self._class_index.get(srr["id"])
                if (not issubclass(srr_class, HostsideResource)) and (not issubclass(srr_class, BaseScannableResource)):
                    collect_phase1(srr["id"])

        if issubclass(resource_class, BaseScannableResource):
            # Delete any StorageResourceOffline alerts
            for alert_state in StorageResourceOffline.objects.filter(alert_item_id=record_id):
                alert_state.delete()

        phase1_ordered_dependencies.append(resource_record.id)

        reference_cache = dict([(r, []) for r in phase1_ordered_dependencies])
        for attr in StorageResourceAttributeReference.objects.filter(value__in=phase1_ordered_dependencies):
            reference_cache[attr.value_id].append(attr)

        def collect_phase2(record_id):
            if record_id in ordered_for_deletion:
                # NB cycles aren't allowed individually in the parent graph,
                # the resourcereference graph, the scoping graph, but
                # we are traversing all 3 at once so we can see cycles here.
                return

            # Find ResourceReference attributes on other objects
            # that refer to this one
            if record_id in reference_cache:
                attrs = reference_cache[record_id]
            else:
                attrs = StorageResourceAttributeReference.objects.filter(value=record_id)
            for attr in attrs:
                collect_phase2(attr.resource_id)

            ordered_for_deletion.append(record_id)

        for record_id in phase1_ordered_dependencies:
            collect_phase2(record_id)

        for storage_resource_record in StorageResourceLearnEvent.objects.all():
            if storage_resource_record.storage_resource.id in ordered_for_deletion:
                storage_resource_record.delete()

        # Delete any parent relations pointing to victim resources
        StorageResourceRecord.parents.through._default_manager.filter(
            **{"%s__in" % StorageResourceRecord.parents.field.m2m_reverse_field_name(): ordered_for_deletion}
        ).delete()

        record_id_to_volumes = defaultdict(list)
        volumes = Volume.objects.filter(storage_resource__in=ordered_for_deletion)
        for v in volumes:
            record_id_to_volumes[v.storage_resource_id].append(v)

        record_id_to_volume_nodes = defaultdict(list)
        volume_nodes = VolumeNode.objects.filter(storage_resource__in=ordered_for_deletion)
        for v in volume_nodes:
            record_id_to_volume_nodes[v.storage_resource_id].append(v)

        for record_id in ordered_for_deletion:
            volume_nodes = record_id_to_volume_nodes[record_id]
            log.debug("%s lun_nodes depend on %s" % (len(volume_nodes), record_id))
            for volume_node in volume_nodes:
                self._remove_volume_node(volume_node, True)

        # Ensure any remaining Volumes (in use by target) are disconnected from storage resource. This is a horrible
        # piece of code that glosses over some of the failings. I did try and remove it for 3.1 but realised it should
        # basically be a null action because no hits should occur and if it is not a null action then it saves us from
        # something that wasn't expected.
        # Example failing: Volume Resource is removed before a VolumeNode resource!
        Volume._base_manager.filter(storage_resource__in=ordered_for_deletion).update(storage_resource=None)
        VolumeNode._base_manager.filter(storage_resource__in=ordered_for_deletion).update(storage_resource=None)

        victim_sras = StorageResourceAlert.objects.filter(alert_item_id__in=ordered_for_deletion).values("id")
        victim_saps = StorageAlertPropagated.objects.filter(alert_state__in=victim_sras).values("id")

        with DelayedContextFrom(StorageAlertPropagated) as sap_delayed:
            [sap_delayed.delete(int(x["id"])) for x in victim_saps]

        for sra in victim_sras:
            storage_resource_alert = StorageResourceAlert.objects.get(id=sra["id"])
            if storage_resource_alert.active:
                StorageResourceAlert.notify(
                    storage_resource_alert.alert_item,
                    False,
                    alert_class=storage_resource_alert.alert_class,
                    attribute=storage_resource_alert.attribute,
                    alert_type=storage_resource_alert.alert_type,
                )

        for record_id in ordered_for_deletion:
            self._subscriber_index.remove_resource(record_id, self._class_index.get(record_id))
            self._class_index.remove_record(record_id)
            self._edges.remove_node(record_id)

            for session in self._sessions.values():
                try:
                    local_id = session.global_id_to_local_id[record_id]
                    del session.local_id_to_global_id[local_id]
                    del session.global_id_to_local_id[record_id]
                    del self._label_cache[record_id]
                except KeyError:
                    pass

        with DelayedContextFrom(StorageResourceRecord) as resources:
            for record_id in ordered_for_deletion:
                resources.update({"id": int(record_id), "storage_id_scope_id": None})

        for klass in [StorageResourceAttributeReference, StorageResourceAttributeSerialized]:
            klass.objects.filter(resource__in=ordered_for_deletion).delete()

        with DelayedContextFrom(StorageResourceRecord) as deleter:
            for record_id in ordered_for_deletion:
                deleter.delete(int(record_id))

    def global_remove_resource(self, resource_id):
        with self._instance_lock:
            with transaction.atomic():
                log.debug("global_remove_resource: %s" % resource_id)
                try:
                    record = StorageResourceRecord.objects.get(pk=resource_id)
                except StorageResourceRecord.DoesNotExist:
                    log.error(
                        "ResourceManager received invalid request to remove non-existent resource %s" % resource_id
                    )
                    return

                self._delete_resource(record)

    def _record_find_ancestor(self, record_id, parent_klass):
        """Find an ancestor of type parent_klass, search depth first"""
        record_class = self._class_index.get(record_id)
        if issubclass(record_class, parent_klass):
            return record_id

        for p in self._edges.get_parents(record_id):
            found = self._record_find_ancestor(p, parent_klass)
            if found:
                return found

        return None

    def _record_find_descendent(self, record_id, descendent_klass, stop_at=None, depth=0):
        """Find a descendent of class dependent_klass, where the trace
        between the origin and the descendent contains no resources of
        class stop_at"""
        record_class = self._class_index.get(record_id)
        if issubclass(record_class, descendent_klass):
            return record_id
        if depth != 0 and stop_at and issubclass(record_class, stop_at):
            return None

        for c in self._edges.get_children(record_id):
            found = self._record_find_descendent(c, descendent_klass, stop_at, depth + 1)
            if found:
                return found

        return None

    def _record_find_ancestors(self, record_id, parent_klass):
        """Find all ancestors of type parent_klass"""
        result = []
        record_class = self._class_index.get(record_id)
        if issubclass(record_class, parent_klass):
            result.append(record_id)

        for p in self._edges.get_parents(record_id):
            result.extend(self._record_find_ancestors(p, parent_klass))

        return result

    def _persist_new_resources(self, session, resources):
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager

        # Must be run in a transaction to avoid leaving invalid things in the DB on failure.
        assert not transaction.get_autocommit()

        # Sort the resources into an order based on ResourceReference
        # attributes, such that the referenced resource is created
        # before the referencing resource.
        ordered_for_creation = []

        def order_by_references(resource):
            if resource._handle_global:
                # Bit of _a weird one: this covers the case where a plugin session
                # was given a root resource that had some ResourceReference attributes
                # that pointed to resources from a different plugin
                return False

            if resource._handle in session.local_id_to_global_id:
                return False

            resource_class, resource_class_id = storage_plugin_manager.get_plugin_resource_class(
                resource.__class__.__module__, resource.__class__.__name__
            )

            # Find any ResourceReference attributes ensure that the target
            # resource gets constructed before this one
            for key, value in resource._storage_dict.items():
                # Special case for ResourceReference attributes, because the resource
                # object passed from the plugin won't have a global ID for the referenced
                # resource -- we have to do the lookup inside ResourceManager
                attribute_obj = resource_class.get_attribute_properties(key)
                if isinstance(attribute_obj, attributes.ResourceReference):
                    if value:
                        referenced_resource = value
                        if not referenced_resource._handle_global:
                            if not referenced_resource._handle in session.local_id_to_global_id:
                                order_by_references(referenced_resource)

            if not resource in ordered_for_creation:
                ordered_for_creation.append(resource)

        for resource in resources:
            if not resource in ordered_for_creation:
                order_by_references(resource)

        # Create StorageResourceRecords for any resources which
        # do not already have one, and update the local_id_to_global_id
        # map with the DB ID for each resource.
        creations = {}
        for resource in ordered_for_creation:
            if isinstance(resource._meta.identifier, BaseScopedId):
                scope_id = session.scannable_id
            elif isinstance(resource._meta.identifier, BaseGlobalId):
                scope_id = None
            else:
                raise NotImplementedError

            resource_class, resource_class_id = storage_plugin_manager.get_plugin_resource_class(
                resource.__class__.__module__, resource.__class__.__name__
            )

            id_tuple = resource.id_tuple()
            cleaned_id_items = []
            for t in id_tuple:
                if isinstance(t, BaseStorageResource):
                    cleaned_id_items.append(session.local_id_to_global_id[t._handle])
                else:
                    cleaned_id_items.append(t)

            id_str = json.dumps(tuple(cleaned_id_items))

            record, created = StorageResourceRecord.objects.get_or_create(
                resource_class_id=resource_class_id, storage_id_str=id_str, storage_id_scope_id=scope_id
            )

            session.local_id_to_global_id[resource._handle] = record.pk
            session.global_id_to_local_id[record.pk] = resource._handle
            self._label_cache[record.id] = resource.get_label()

            if created:
                # Record a user-visible event
                log.debug(
                    "ResourceManager._persist_new_resource[%s] %s %s %s"
                    % (session.scannable_id, created, record.pk, resource._handle)
                )

            creations[resource] = (record, created)

            # Add the new record to the index so that future records and resolve their
            # provide/subscribe relationships with respect to it
            self._subscriber_index.add_resource(record.pk, resource)

            self._class_index.add_record(record.pk, resource_class)

        # Update or create attribute records
        attr_classes = set()
        for resource in ordered_for_creation:
            record, created = creations[resource]

            if isinstance(resource._meta.identifier, BaseGlobalId) and session.scannable_id != record.id:
                try:
                    record.reported_by.get(pk=session.scannable_id)
                except StorageResourceRecord.DoesNotExist:
                    log.debug(
                        "saw GlobalId resource %s from scope %s for the first time" % (record.id, session.scannable_id)
                    )
                    record.reported_by.add(session.scannable_id)

            resource_class = storage_plugin_manager.get_resource_class_by_id(record.resource_class_id)

            attrs = {}
            # Special case for ResourceReference attributes, because the resource
            # object passed from the plugin won't have a global ID for the referenced
            # resource -- we have to do the lookup inside ResourceManager
            for key, value in resource._storage_dict.items():
                attribute_obj = resource_class.get_attribute_properties(key)
                if isinstance(attribute_obj, attributes.ResourceReference):
                    if value and not value._handle_global:
                        attrs[key] = session.local_id_to_global_id[value._handle]
                    elif value and value._handle_global:
                        attrs[key] = value._handle
                    else:
                        attrs[key] = value
                else:
                    attrs[key] = value

            for key, val in attrs.items():
                resource_class = storage_plugin_manager.get_resource_class_by_id(record.resource_class_id)

                # Try to update an existing record
                attr_model_class = resource_class.attr_model_class(key)

                updated = attr_model_class.objects.filter(resource=record, key=key).update(
                    value=attr_model_class.encode(val)
                )

                # If there was no existing record, create one
                if not updated:
                    delayed_attr_model_class = DelayedContextFrom(attr_model_class)

                    attr_classes.add(delayed_attr_model_class)

                    if issubclass(attr_model_class, StorageResourceAttributeSerialized):
                        data = dict(resource_id=record.id, key=key, value=attr_model_class.encode(val))
                    else:
                        data = dict(resource_id=record.id, key=key, value_id=attr_model_class.encode(val))

                    delayed_attr_model_class.insert(data)

        [x.item_cache.flush() for x in attr_classes]

        # Find out if new resources match anything in SubscriberIndex and create
        # relationships if so.
        logicaldrives_with_new_descendents = []
        for resource in ordered_for_creation:
            record, created = creations[resource]
            if created:
                # This is a new resource which provides a field, see if any existing
                # resources would like to subscribe to it
                subscribers = self._subscriber_index.what_subscribes(resource)
                # Make myself a parent of anything that subscribes to me
                for s in subscribers:
                    if s == record.pk:
                        continue
                    log.info("Linked up me %s as parent of %s" % (record.pk, s))
                    self._edges.add_parent(s, record.pk)
                    s_record = StorageResourceRecord.objects.get(pk=s)
                    s_record.parents.add(record.pk)
                    if isinstance(resource, LogicalDrive):
                        # A new LogicalDrive ancestor might affect the labelling
                        # of another LogicalDrive's Volume.
                        logicaldrives_with_new_descendents.append(record.id)

                # This is a new resource which subscribes to a field, see if any existing
                # resource can provide it
                providers = self._subscriber_index.what_provides(resource)
                # Make my providers my parents
                for p in providers:
                    if p == record.pk:
                        continue
                    log.info("Linked up %s as parent of me, %s" % (p, record.pk))
                    self._edges.add_parent(record.pk, p)
                    record.parents.add(p)

        # Update EdgeIndex and StorageResourceRecord.parents
        for resource in resources:
            try:
                record, created = creations[resource]
            except KeyError:
                record = StorageResourceRecord.objects.get(pk=session.local_id_to_global_id[resource._handle])

            # Update self._edges
            for p in resource._parents:
                parent_global_id = session.local_id_to_global_id[p._handle]
                self._edges.add_parent(record.id, parent_global_id)

            new_parent_pks = [session.local_id_to_global_id[p._handle] for p in resource._parents]
            record.parents.add(*new_parent_pks)

        # For any LogicalDrives we created that have been hooked up via SubscriberIndex,
        # see if their presence should change the name of a Volume
        for ld_id in logicaldrives_with_new_descendents:
            for c in self._edges.get_children(ld_id):
                descendent_ld = self._record_find_descendent(c, LogicalDrive)
                if descendent_ld:
                    ancestors = self._record_find_ancestors(descendent_ld, LogicalDrive)
                    ancestors.remove(descendent_ld)
                    if len(ancestors) == 1:
                        Volume.objects.filter(storage_resource=descendent_ld).update(label=self.get_label(ld_id))

        # Create StorageResourceLearnEvent for anything we found new
        for resource in creations:
            record, created = creations[resource]

            if created and hasattr(session, "host_id"):
                StorageResourceLearnEvent.register_event(
                    severity=logging.INFO,
                    alert_item=ManagedHost.objects.get(id=getattr(session, "host_id")),
                    storage_resource=record,
                )
