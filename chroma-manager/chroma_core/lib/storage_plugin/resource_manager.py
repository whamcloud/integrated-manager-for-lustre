#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


"""The resource manager is the home of the global view of the resources populated from
all plugins.  BaseStoragePlugin instances have their own local caches of resources, which
they use to periodically update this central store.

Concurrency:
    This code is written for multi-threaded use within a single process.
    It is not safe to have multiple processes running plugins at this stage.
    We serialize operations from different plugins using a big lock, and
    we use the autocommit decorator on persistence functions because
    otherwise we would have to explicitly commit at the start of
    each one to see changes from other threads.

WARNING:
    There is a global instance of ResourceManager initialized in this module, and
    its initialization does a significant amount of DB activity.  Don't import
    this module unless you're really going to use it.
"""
import logging
from django.db.models.aggregates import Count
from django.db.models.query_utils import Q
from chroma_core.lib.storage_plugin.api import attributes, relations
from chroma_core.lib.storage_plugin.base_resource import BaseGlobalId, BaseScopedId, HostsideResource, BaseScannableResource
from chroma_core.lib.storage_plugin.base_resource import BaseStorageResource

from chroma_core.lib.storage_plugin.log import storage_plugin_log as log
from chroma_core.lib.util import all_subclasses

from chroma_core.models import ManagedHost, ManagedTarget
from chroma_core.models import Volume, VolumeNode
from chroma_core.models import StorageResourceRecord, StorageResourceStatistic
from chroma_core.models import StorageResourceAlert, StorageResourceOffline
from chroma_core.models.alert import AlertState

from django.db import transaction

from collections import defaultdict
import threading
from chroma_core.models.storage_plugin import StorageResourceAttributeSerialized, StorageResourceLearnEvent, StorageResourceAttributeReference, StorageAlertPropagated
from chroma_core.models.target import ManagedTargetMount


class PluginSession(object):
    def __init__(self, scannable_id, update_period):
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
        for srr in StorageResourceRecord.objects.filter(~Q(parents = None)).values('id', 'parents'):
            child = srr['id']
            parent = srr['parents']
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
            result = StorageResourceRecord.objects.get(pk = record_id).resource_class.get_class()
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
        for srr in StorageResourceRecord.objects.all().values('id', 'resource_class_id'):
            self.add_record(srr['id'], storage_plugin_manager.get_resource_class_by_id(srr['resource_class_id']))


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
                resource = StorageResourceRecord.objects.get(pk = resource_id).to_resource()
                log.debug("SubscriberIndex.remove provider %s" % subscription.key)
                self.remove_provider(resource_id, subscription.key, subscription.val(resource))
        log.debug("subscriptions = %s" % resource_class._meta.subscriptions)
        for subscription in resource_class._meta.subscriptions:
            # FIXME: performance: only load the attr we need instead of whole resource
            resource = StorageResourceRecord.objects.get(pk = resource_id).to_resource()
            log.debug("SubscriberIndex.remove subscriber %s" % subscription.key)
            self.remove_subscriber(resource_id, subscription.key, subscription.val(resource))

    def populate(self):
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager
        for resource_class_id, resource_class in storage_plugin_manager.get_all_resources():
            for subscription in self._all_subscriptions:
                if issubclass(resource_class, subscription.subscribe_to):
                    records = StorageResourceRecord.objects.filter(
                            resource_class = resource_class_id)
                    for r in records:
                        resource = r.to_resource()
                        self.add_provider(r.id, subscription.key, subscription.val(resource))

            for subscription in resource_class._meta.subscriptions:
                records = StorageResourceRecord.objects.filter(
                        resource_class = resource_class_id)
                for r in records:
                    resource = r.to_resource()
                    self.add_subscriber(r.id, subscription.key, subscription.val(resource))


class ResourceManager(object):
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

        import dse
        dse.patch_models()

    def session_open(self,
            scannable_id,
            initial_resources,
            update_period):
        scannable_class = self._class_index.get(scannable_id)
        assert issubclass(scannable_class, BaseScannableResource) or issubclass(scannable_class, HostsideResource)
        log.debug(">> session_open %s (%s resources)" % (scannable_id, len(initial_resources)))
        with self._instance_lock:
            if scannable_id in self._sessions:
                log.warning("Clearing out old session for scannable ID %s" % scannable_id)
                del self._sessions[scannable_id]

            session = PluginSession(scannable_id, update_period)
            self._sessions[scannable_id] = session
            self._persist_new_resources(session, initial_resources)
            self._cull_lost_resources(session, initial_resources)

            # Update Volume and VolumeNode objects
            self._persist_lun_updates(scannable_id)

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

    @transaction.commit_on_success
    def _persist_created_hosts(self, session, scannable_id, new_resources):
        log.debug("_persist_created_hosts")

        record_pks = []
        from chroma_core.lib.storage_plugin.api.resources import VirtualMachine
        for resource in new_resources:
            if isinstance(resource, VirtualMachine):
                assert(not resource._handle_global)
                record_pks.append(session.local_id_to_global_id[resource._handle])

        for vm_record_pk in record_pks:
            record = StorageResourceRecord.objects.get(pk = vm_record_pk)
            resource = record.to_resource()

            if not resource.host_id:
                try:
                    host = ManagedHost.objects.get(address = resource.address)
                    log.info("Associated existing host with VirtualMachine resource: %s" % resource.address)
                    record.update_attribute('host_id', host.pk)
                except ManagedHost.DoesNotExist:
                    log.info("Creating host for new VirtualMachine resource: %s" % resource.address)
                    host, command = ManagedHost.create_from_string(resource.address)
                    record.update_attribute('host_id', host.pk)

    def _balance_volume_nodes(self, volumes_to_balance, volume_id_to_nodes):
        volume_ids_to_balance = [v.id for v in volumes_to_balance]
        hosts = set()
        for vn_list in volume_id_to_nodes.values():
            for vn in vn_list:
                hosts.add(vn.host_id)

        outer_host_to_primary_count = dict([(host_id, 0) for host_id in hosts])
        outer_host_to_used_count = dict([(host_id, 0) for host_id in hosts])

        host_volumes = Volume.objects.filter(volumenode__host__in = hosts).distinct()
        volume_to_volume_nodes = defaultdict(list)
        all_vns = []
        for vn in VolumeNode.objects.filter(volume__in = host_volumes):
            volume_to_volume_nodes[vn.volume_id].append(vn)
            all_vns.append(vn)

        for vn in all_vns:
            if vn.host_id in hosts:
                if vn.primary:
                    if len(volume_to_volume_nodes[vn.volume_id]) > 1:
                        if not vn.volume_id in volume_ids_to_balance:
                            outer_host_to_primary_count[vn.host_id] += 1
                if vn.use:
                    if not vn.volume_id in volume_ids_to_balance:
                        outer_host_to_used_count[vn.host_id] += 1

        with VolumeNode.delayed as vn_writer:
            for volume_id in volume_ids_to_balance:
                volume_nodes = volume_to_volume_nodes[volume_id]
                host_to_lun_nodes = defaultdict(list)
                for vn in volume_nodes:
                    host_to_lun_nodes[vn.host_id].append(vn)

                host_to_primary_count = {}
                for host_id in host_to_lun_nodes.keys():
                    # Instead of just counting primary nodes (that would include local volumes), only
                    # give a host credit for a primary node if the node's volume also has a secondary
                    # somewhere.
                    primary_count = outer_host_to_primary_count[host_id]
                    host_to_primary_count[host_id] = primary_count
                    log.info("primary_count %s = %s" % (host_id, primary_count))

                fewest_primaries = [host_id for host_id, count in sorted(host_to_primary_count.items(), lambda x, y: cmp(x[1], y[1]))][0]
                primary_lun_node = host_to_lun_nodes[fewest_primaries][0]
                outer_host_to_primary_count[fewest_primaries] += 1
                outer_host_to_used_count[fewest_primaries] += 1
                vn_writer.update(
                    {'id': primary_lun_node.id,
                     'use': True,
                     'primary': True
                    })
                log.info("affinity_balance: picked %s for %s primary" % (primary_lun_node.host_id, volume_id))

                # Remove the primary host from consideration for the secondary mount
                del host_to_lun_nodes[primary_lun_node.host_id]

                if len(host_to_lun_nodes) > 0:
                    host_to_used_node_count = dict([(h, outer_host_to_used_count[h]) for h in host_to_lun_nodes.keys()])
                    fewest_used_nodes = [host for host, count in sorted(host_to_used_node_count.items(), lambda x, y: cmp(x[1], y[1]))][0]
                    outer_host_to_used_count[fewest_used_nodes] += 1
                    secondary_lun_node = host_to_lun_nodes[fewest_used_nodes][0]

                    vn_writer.update({
                        'id': secondary_lun_node.id,
                        'use': True,
                        'primary': False
                    })

                    log.info("affinity_balance: picked %s for %s volume secondary" % (secondary_lun_node.host_id, volume_id))
                else:
                    secondary_lun_node = None

                for volume_node in volume_nodes:
                    if not volume_node in (primary_lun_node, secondary_lun_node):
                        vn_writer.update({
                            'id': volume_node.id,
                            'use': False,
                            'primary': False
                        })

    @transaction.commit_on_success
    def _persist_lun_updates(self, scannable_id):
        from chroma_core.lib.storage_plugin.query import ResourceQuery
        from chroma_core.lib.storage_plugin.api.resources import PathWeight, DeviceNode, LogicalDrive
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager
        from chroma_core.lib.storage_plugin.base_resource import HostsideResource

        scannable_resource = ResourceQuery().get_resource(scannable_id)

        if not isinstance(scannable_resource, HostsideResource):
            return
        else:
            log.debug("_persist_lun_updates for scope record %s" % scannable_id)
            host = ManagedHost.objects.get(pk = scannable_resource.host_id)

        # Get all DeviceNodes within this scope
        node_klass_ids = [storage_plugin_manager.get_resource_class_id(klass)
                for klass in all_subclasses(DeviceNode)]

        node_resources = StorageResourceRecord.objects.filter(
            resource_class__in = node_klass_ids, storage_id_scope = scannable_id).annotate(
            child_count = Count('resource_parent'))

        # DeviceNodes elegible for use as a VolumeNode (leaves)
        usable_node_resources = [nr for nr in node_resources if nr.child_count == 0]

        # DeviceNodes which are usable but don't have VolumeNode
        assigned_resource_ids = [ln['storage_resource_id'] for ln in VolumeNode.objects.filter(storage_resource__in = [n.id for n in node_resources]).values("id", "storage_resource_id")]
        unassigned_node_resources = [nr for nr in usable_node_resources if nr.id not in assigned_resource_ids]

        # VolumeNodes whose storage resource is within this scope
        scope_volume_nodes = VolumeNode.objects.filter(storage_resource__storage_id_scope = scannable_id)

        log.debug("%s %s %s %s" % (tuple([len(l) for l in [node_resources, usable_node_resources, unassigned_node_resources, scope_volume_nodes]])))

        def affinity_weights(volume, volume_nodes):
            weights = {}
            for volume_node in volume_nodes:
                if not volume_node.storage_resource_id:
                    log.info("affinity_weights: no storage_resource for VolumeNode %s" % volume_node.id)
                    return False

                weight_resource_ids = self._record_find_ancestors(volume_node.storage_resource_id, PathWeight)
                if len(weight_resource_ids) == 0:
                    log.info("affinity_weights: no PathWeights for VolumeNode %s" % volume_node.id)
                    return False

                attr_model_class = StorageResourceRecord.objects.get(id = weight_resource_ids[0]).resource_class.get_class().attr_model_class('weight')

                import json
                ancestor_weights = [json.loads(w['value']) for w in attr_model_class.objects.filter(
                    resource__in = weight_resource_ids, key = 'weight').values('value')]
                weight = reduce(lambda x, y: x + y, ancestor_weights)
                weights[volume_node] = weight

            log.info("affinity_weights: %s" % weights)

            sorted_volume_nodes = [volume_node for volume_node, weight in sorted(weights.items(), lambda x, y: cmp(x[1], y[1]))]
            sorted_volume_nodes.reverse()
            primary = sorted_volume_nodes[0]
            primary.primary = True
            primary.use = True
            primary.save()
            if len(sorted_volume_nodes) > 1:
                secondary = sorted_volume_nodes[1]
                secondary.use = True
                secondary.primary = False
                secondary.save()
            for volume_node in sorted_volume_nodes[2:]:
                volume_node.use = False
                volume_node.primary = False
                volume_node.save()

            return True

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

        # Get the sizes for all of the logicaldrive resources
        sizes = StorageResourceAttributeSerialized.objects.filter(
            resource__id__in = node_to_logicaldrive_id.values(), key = 'size').values('resource_id', 'value')
        logicaldrive_id_to_size = dict([(s['resource_id'],
                                    StorageResourceAttributeSerialized.decode(s['value'])) for s in sizes])

        existing_volumes = Volume.objects.filter(storage_resource__in = node_to_logicaldrive_id.values())
        logicaldrive_id_to_volume = dict([(v.storage_resource_id, v) for v in existing_volumes])
        with Volume.delayed as volumes:
            for node_resource, logicaldrive_id in node_to_logicaldrive_id.items():
                if not logicaldrive_id in logicaldrive_id_to_volume:
                    size = logicaldrive_id_to_size[logicaldrive_id]
                    volumes.insert(dict(
                        size = size,
                        storage_resource_id = logicaldrive_id,
                        not_deleted = True,
                        label = ""
                    ))

        existing_volumes = Volume.objects.filter(storage_resource__in = node_to_logicaldrive_id.values())
        logicaldrive_id_to_volume = dict([(v.storage_resource_id, v) for v in existing_volumes])

        path_attrs = StorageResourceAttributeSerialized.objects.filter(key = 'path', resource__in = unassigned_node_resources).values('resource_id', 'value')
        node_record_id_to_path = dict([(
            p['resource_id'], StorageResourceAttributeSerialized.decode(p['value'])
        ) for p in path_attrs])

        existing_volume_nodes = VolumeNode.objects.filter(host = host, path__in = node_record_id_to_path.values())
        path_to_volumenode = dict([(
            vn.path, vn
        ) for vn in existing_volume_nodes])

        with VolumeNode.delayed as volume_nodes:
            for node_record in unassigned_node_resources:
                volume = logicaldrive_id_to_volume[node_to_logicaldrive_id[node_record]]
                log.info("Setting up DeviceNode %s" % node_record.pk)
                path = node_record_id_to_path[node_record.id]
                if path in path_to_volumenode:
                    volume_node = path_to_volumenode[path]
                else:
                    volume_nodes.insert(dict(
                        volume_id = volume.id,
                        host_id = host.id,
                        path = path,
                        storage_resource_id = node_record.pk,
                        primary = False,
                        use = False,
                        not_deleted = True
                    ))

                    log.info("Created VolumeNode for resource %s" % node_record.pk)
                    volumes_for_affinity_checks.add(volume)

        volume_to_volume_nodes = defaultdict(list)
        for vn in VolumeNode.objects.filter(volume__in = volumes_for_affinity_checks):
            volume_to_volume_nodes[vn.volume_id].append(vn)

        occupied_volumes = set([t['volume_id'] for t in ManagedTarget.objects.filter(volume__in = volumes_for_affinity_checks).values('volume_id')])
        volumes_for_affinity_checks = [v for v in volumes_for_affinity_checks if v.id not in occupied_volumes and volume_to_volume_nodes[v.id]]

        volumes_for_balancing = []
        for volume in volumes_for_affinity_checks:
            got_weights = affinity_weights(volume, volume_to_volume_nodes[volume.id])
            if not got_weights:
                volumes_for_balancing.append(volume)

        self._balance_volume_nodes(volumes_for_balancing, volume_to_volume_nodes)

        # For all VolumeNodes, if its storage resource was in this scope, and it
        # was not included in the set of usable DeviceNode resources, remove
        # the VolumeNode
        for volume_node in scope_volume_nodes:
            log.debug("volume node %s (%s) usable %s" % (volume_node.id, volume_node.storage_resource_id, volume_node.storage_resource_id in [nr.id for nr in usable_node_resources]))
            if not volume_node.storage_resource_id in [nr.id for nr in usable_node_resources]:
                removed = self._try_removing_volume_node(volume_node)
                if not removed:
                    volume_node.storage_resource = None
                    volume_node.save()

        # TODO: Volume Stealing: there may be an existing Volume/VolumeNode setup for some ScsiDeviceNodes and ScsiVolumes
        # detected by Chroma, and a storage plugin adds in extra links to the device nodes that follow back
        # to a LogicalDrive provided by the plugin.  In this case there are two LogicalDrive ancestors of the
        # device nodes and we would like to have the Volume refer to the plugin-provided one rather than
        # the auto-generated one (to get the right name etc).
        # LogicalDrives within this scope
        #logical_drive_klass_ids = [storage_plugin_manager.get_resource_class_id(klass)
        #        for klass in all_subclasses(resources.LogicalDrive)]
        #logical_drive_resources = ResourceQuery().get_class_resources(logical_drive_klass_ids, storage_id_scope = scannable_id)

    def _try_removing_volume(self, volume):
        targets = ManagedTarget.objects.filter(volume = volume)
        nodes = VolumeNode.objects.filter(volume = volume)
        if targets.count() == 0 and nodes.count() == 0:
            log.warn("Removing Volume %s" % volume.id)
            volume.storage_resource = None
            volume.save()
            Volume.delete(volume.id)
            return True
        elif targets.count():
            log.warn("Leaving Volume %s, used by Target %s" % (volume.id, targets[0]))
        elif nodes.count():
            log.warn("Leaving Volume %s, used by %s nodes" % (volume.id, nodes.count()))

        return False

    def _try_removing_volume_node(self, volume_node):
        targets = ManagedTarget.objects.filter(managedtargetmount__volume_node = volume_node)
        if targets.count() == 0:
            log.warn("Removing VolumeNode %s" % volume_node.id)
            VolumeNode.delete(volume_node.id)
            self._try_removing_volume(volume_node.volume)
            return True
        else:
            log.warn("Leaving VolumeNode %s, used by Target %s" % (volume_node.id, targets[0]))

        return False

    def session_update_resource(self, scannable_id, local_resource_id, attrs):
        #with self._instance_lock:
        #    session = self._sessions[scannable_id]
        #    record_pk = session.local_id_to_global_id[local_resource_id]
        #    # TODO: implement
        pass

    def session_resource_add_parent(self, scannable_id, local_resource_id, local_parent_id):
        with self._instance_lock:
            session = self._sessions[scannable_id]
            record_pk = session.local_id_to_global_id[local_resource_id]
            parent_pk = session.local_id_to_global_id[local_parent_id]
            self._edges.add_parent(record_pk, parent_pk)
            self._resource_modify_parent(record_pk, parent_pk, False)

    def session_resource_remove_parent(self, scannable_id, local_resource_id, local_parent_id):
        with self._instance_lock:
            session = self._sessions[scannable_id]
            record_pk = session.local_id_to_global_id[local_resource_id]
            parent_pk = session.local_id_to_global_id[local_parent_id]
            self._edges.remove_parent(record_pk, parent_pk)
            self._resource_modify_parent(record_pk, parent_pk, True)

    def session_update_stats(self, scannable_id, local_resource_id, update_data):
        """Get global ID for a resource, look up the StoreageResourceStatistic for
           each stat in the update, and invoke its .metrics.update with the data"""
       # FIXME: definitely could be doing finer grained locking here as although
       # we need the coarse one for protecting local_id_to_global_id etc, the later
       # part of actually updating stats just needs to be locked on a per-statistic basis
        with self._instance_lock:
                session = self._sessions[scannable_id]
                record_pk = session.local_id_to_global_id[local_resource_id]
                self._persist_update_stats(record_pk, update_data)

    @transaction.autocommit
    def _persist_update_stats(self, record_pk, update_data):
        record = StorageResourceRecord.objects.get(pk = record_pk)
        for stat_name, stat_data in update_data.items():
            stat_properties = record.get_statistic_properties(stat_name)
            try:
                stat_record = StorageResourceStatistic.objects.get(
                        storage_resource = record, name = stat_name)
                if stat_record.sample_period != stat_properties.sample_period:
                    log.warning("Plugin stat period for '%s' changed, expunging old statistics", stat_name)
                    stat_record.delete()
                    raise StorageResourceStatistic.DoesNotExist

            except StorageResourceStatistic.DoesNotExist:
                stat_record = StorageResourceStatistic.objects.create(
                        storage_resource = record, name = stat_name, sample_period = stat_properties.sample_period)
            from r3d.exceptions import BadUpdateString, BadUpdateTime
            try:
                # FIXME: I should be allowed to insert stats as often as I like
                # but r3d complains if it hasn't been more than N seconds since
                # my last update
                try:
                    stat_record.update(stat_name, stat_properties, stat_data)
                except BadUpdateTime:
                    pass
            except BadUpdateString:
                # FIXME: Initial insert usually fails because r3d isn't getting
                # its start time from the first insert time
                pass

    @transaction.autocommit
    def _resource_modify_parent(self, record_pk, parent_pk, remove):
        from chroma_core.models import StorageResourceRecord
        record = StorageResourceRecord.objects.get(pk = record_pk)
        if remove:
            record.parents.remove(parent_pk)
        else:
            record.parents.add(parent_pk)

    @transaction.autocommit
    def _resource_persist_update_attributes(self, record_pk, attrs):
        from chroma_core.models import StorageResourceRecord
        record = StorageResourceRecord.objects.get(record_pk)
        record.update_attributes(attrs)

    def session_add_resources(self, scannable_id, resources):
        """NB this is plural because new resources may be interdependent
        and if so they must be added in a blob so that we can hook up the
        parent relationships"""
        with self._instance_lock:
            session = self._sessions[scannable_id]
            self._persist_new_resources(session, resources)
            self._persist_lun_updates(scannable_id)
            self._persist_created_hosts(session, scannable_id, resources)

    def session_remove_resources(self, scannable_id, resources):
        with self._instance_lock:
            session = self._sessions[scannable_id]
            for local_resource in resources:
                try:
                    resource_global_id = session.local_id_to_global_id[local_resource._handle]
                    self._delete_resource(StorageResourceRecord.objects.get(pk = resource_global_id))
                except KeyError:
                    pass
            self._persist_lun_updates(scannable_id)

    def session_notify_alert(self, scannable_id, resource_local_id, active, alert_class, attribute):
        with self._instance_lock:
            session = self._sessions[scannable_id]
            record_pk = session.local_id_to_global_id[resource_local_id]
            if active:
                if not (record_pk, alert_class) in self._active_alerts:
                    alert_state = self._persist_alert(record_pk, active, alert_class, attribute)
                    self._persist_alert_propagate(alert_state)
                    self._active_alerts[(record_pk, alert_class)] = alert_state.pk
            else:
                alert_state = self._persist_alert(record_pk, active, alert_class, attribute)
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
            sap, created = StorageAlertPropagated.objects.get_or_create(
                    storage_resource_id = d,
                    alert_state = alert_state)

    def _persist_alert_unpropagate(self, alert_state):
        StorageAlertPropagated.objects.filter(alert_state = alert_state).delete()

    # FIXME: Couple of issues here:
    # * The AlertState subclasses use Downcastable, they need to be in a transaction
    #   for creations.
    # * If we _persist_alert down, then lose power, we will forget all about the alert
    #   before we remove the PropagatedAlerts for it: actually need to do a two step
    #   removal where we check if there's something there, and if there is then we
    #   remove the propagated alerts, and then finally mark inactive the alert itself.
    @transaction.autocommit
    def _persist_alert(self, record_pk, active, alert_class, attribute):
        record = StorageResourceRecord.objects.get(pk = record_pk)
        alert_state = StorageResourceAlert.notify(record, active, alert_class=alert_class, attribute=attribute)
        return alert_state

    @transaction.autocommit
    def _cull_lost_resources(self, session, reported_resources):
        reported_scoped_resources = []
        reported_global_resources = []
        for r in reported_resources:
            if isinstance(r._meta.identifier, BaseScopedId):
                reported_scoped_resources.append(session.local_id_to_global_id[r._handle])
            else:
                reported_global_resources.append(session.local_id_to_global_id[r._handle])

        lost_resources = StorageResourceRecord.objects.filter(
                ~Q(pk__in = reported_scoped_resources),
                storage_id_scope = session.scannable_id)
        for r in lost_resources:
            self._delete_resource(r)

        # Look for globalid resources which were at some point reported by
        # this scannable_id, but are missing this time around
        forgotten_global_resources = StorageResourceRecord.objects.filter(
                ~Q(pk__in = reported_global_resources),
                reported_by = session.scannable_id)
        for reportee in forgotten_global_resources:
            reportee.reported_by.remove(session.scannable_id)
            if not reportee.reported_by.count():
                self._delete_resource(reportee)

    def _delete_resource(self, resource_record):
        log.info("ResourceManager._cull_resource '%s'" % resource_record.pk)

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
            for dependent in StorageResourceRecord.objects.filter(storage_id_scope = record_id):
                collect_phase1(dependent.id)

            # Delete any reported_by relations to this resource
            StorageResourceRecord.reported_by.through._default_manager.filter(
                **{'%s' % StorageResourceRecord.reported_by.field.m2m_reverse_field_name(): record_id}
            ).delete()

            # Delete any resources whose reported_by are now zero
            for srr in StorageResourceRecord.objects.filter(storage_id_scope = None, reported_by = None).values('id'):
                srr_class = self._class_index.get(srr['id'])
                if (not issubclass(srr_class, HostsideResource)) and (not issubclass(srr_class, BaseScannableResource)):
                    collect_phase1(srr['id'])

        if issubclass(resource_class, BaseScannableResource):
            # Delete any StorageResourceOffline alerts
            for alert_state in StorageResourceOffline.objects.filter(alert_item_id = record_id):
                alert_state.delete()

        phase1_ordered_dependencies.append(resource_record.id)

        reference_cache = dict([(r, []) for r in phase1_ordered_dependencies])
        for attr in StorageResourceAttributeReference.objects.filter(value__in = phase1_ordered_dependencies):
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
                attrs = StorageResourceAttributeReference.objects.filter(value = record_id)
            for attr in attrs:
                collect_phase2(attr.resource_id)

            ordered_for_deletion.append(record_id)

        for record_id in phase1_ordered_dependencies:
            collect_phase2(record_id)

        # Delete any parent relations pointing to victim resources
        StorageResourceRecord.parents.through._default_manager.filter(
            **{'%s__in' % StorageResourceRecord.parents.field.m2m_reverse_field_name(): ordered_for_deletion}
        ).delete()

        record_id_to_volumes = defaultdict(list)
        volumes = Volume.objects.filter(storage_resource__in = ordered_for_deletion)
        for v in volumes:
            record_id_to_volumes[v.storage_resource_id].append(v)

        record_id_to_volume_nodes = defaultdict(list)
        volume_nodes = VolumeNode.objects.filter(storage_resource__in = ordered_for_deletion)
        for v in volume_nodes:
            record_id_to_volume_nodes[v.storage_resource_id].append(v)

        occupiers = ManagedTargetMount.objects.filter(managedtarget__not_deleted = True).filter(volume_node__in = volume_nodes)
        vn_id_to_occupiers = defaultdict(list)
        for mtm in occupiers:
            vn_id_to_occupiers[mtm.volume_node_id].append(mtm)

        volumes_need_attention = []
        for record_id in ordered_for_deletion:
            volume_nodes = record_id_to_volume_nodes[record_id]
            log.debug("%s lun_nodes depend on %s" % (len(volume_nodes), record_id))
            for volume_node in volume_nodes:
                if vn_id_to_occupiers[volume_node.id]:
                    log.warn("Leaving VolumeNode %s, used by Target" % volume_node.id)
                    log.warning("Could not remove VolumeNode %s, disconnecting from resource %s" % (volume_node.id, record_id))
                else:
                    log.warn("Removing VolumeNode %s" % volume_node.id)
                    VolumeNode.delayed.update({'id': volume_node.id, 'not_deleted': None})
                    volumes_need_attention.append(volume_node.volume_id)

            volumes_need_attention.extend(record_id_to_volumes[record_id])

        VolumeNode.delayed.flush()

        volume_to_targets = defaultdict(list)
        for mt in ManagedTarget.objects.filter(volume__in = volumes_need_attention):
            volume_to_targets[mt.volume_id].append(mt)

        volume_to_volume_nodes = defaultdict(list)
        for vn in VolumeNode.objects.filter(volume__in = volumes_need_attention):
            volume_to_volume_nodes[vn.volume_id].append(vn)

        for volume_id in volumes_need_attention:
            targets = volume_to_targets[volume_id]
            nodes = volume_to_volume_nodes[volume_id]
            if (not targets) and (not nodes):
                log.warn("Removing Volume %s" % volume_id)
                Volume.delayed.update({'id': volume_id, 'not_deleted': None})
            elif targets:
                log.warn("Leaving Volume %s, used by Target %s" % (volume_id, targets[0]))
            elif nodes:
                log.warn("Leaving Volume %s, used by %s nodes" % (volume_id, len(nodes)))

        Volume.delayed.flush()

        # Ensure any remaining Volumes (in use by target) are disconnected from storage resource
        Volume._base_manager.filter(storage_resource__in = ordered_for_deletion).update(storage_resource = None)
        VolumeNode._base_manager.filter(storage_resource__in = ordered_for_deletion).update(storage_resource = None)

        victim_sras = StorageResourceAlert.objects.filter(alert_item_id__in = ordered_for_deletion).values('id')
        victim_saps = StorageAlertPropagated.objects.filter(alert_state__in = victim_sras).values('id')

        for sap in victim_saps:
            StorageAlertPropagated.delayed.delete(int(sap['id']))
        StorageAlertPropagated.delayed.flush()

        for sra in victim_sras:
            StorageResourceAlert.delayed.delete(int(sra['id']))
        StorageResourceAlert.delayed.flush()

        for sra in victim_sras:
            AlertState.delayed.delete(int(sra['id']))
        AlertState.delayed.flush()

        with StorageResourceStatistic.delayed as srs_delayed:
            for srs in StorageResourceStatistic.objects.filter(storage_resource__in = ordered_for_deletion):
                srs.metrics.clear()
                srs_delayed.delete(int(srs.id))

        for record_id in ordered_for_deletion:
            self._subscriber_index.remove_resource(record_id, self._class_index.get(record_id))
            self._class_index.remove_record(record_id)
            self._edges.remove_node(record_id)

            for session in self._sessions.values():
                try:
                    local_id = session.global_id_to_local_id[record_id]
                    del session.local_id_to_global_id[local_id]
                    del session.global_id_to_local_id[local_id]
                except KeyError:
                    pass

        StorageResourceLearnEvent._base_manager.filter(storage_resource__in = ordered_for_deletion).delete()

        with StorageResourceRecord.delayed as resources:
            for record_id in ordered_for_deletion:
                resources.update({'id': int(record_id), 'storage_id_scope_id': None})

        for klass in [StorageResourceAttributeReference, StorageResourceAttributeSerialized]:
            klass.objects.filter(resource__in = ordered_for_deletion).delete()

        with StorageResourceRecord.delayed as deleter:
            for record_id in ordered_for_deletion:
                deleter.delete(int(record_id))

    def global_remove_resource(self, resource_id):
        with self._instance_lock:
            log.debug("global_remove_resource: %s" % resource_id)
            from chroma_core.models import StorageResourceRecord
            try:
                record = StorageResourceRecord.objects.get(pk = resource_id)
            except StorageResourceRecord.DoesNotExist:
                log.error("ResourceManager received invalid request to remove non-existent resource %s" % resource_id)
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

    def _record_find_ancestors(self, record_id, parent_klass):
        """Find all ancestors of type parent_klass"""
        result = []
        record_class = self._class_index.get(record_id)
        if issubclass(record_class, parent_klass):
            result.append(record_id)

        for p in self._edges.get_parents(record_id):
            result.extend(self._record_find_ancestors(p, parent_klass))

        return result

    # Use commit on success to avoid situations where a resource record
    # lands in the DB without its attribute records.
    # FIXME: there are cases where _persist_new_resource gets called outside
    # of _persist_new_resources, make sure it's wrapped in a transaction too
    @transaction.commit_on_success
    def _persist_new_resources(self, session, resources):
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager

        ordered_for_creation = []

        def order_by_references(resource):
            if resource._handle_global:
                # Bit of _a weird one: this covers the case where a plugin sessoin
                # was given a root resource that had some ResourceReference attributes
                # that pointed to resources from a different plugin
                return False

            if resource._handle in session.local_id_to_global_id:
                return False

            resource_class, resource_class_id = storage_plugin_manager.get_plugin_resource_class(
                resource.__class__.__module__,
                resource.__class__.__name__)

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
                                ordered_for_creation.append(referenced_resource)

            return True

        for resource in resources:
            if not resource in ordered_for_creation:
                if order_by_references(resource):
                    ordered_for_creation.append(resource)

        creations = {}
        for resource in ordered_for_creation:
            if isinstance(resource._meta.identifier, BaseScopedId):
                scope_id = session.scannable_id
            elif isinstance(resource._meta.identifier, BaseGlobalId):
                scope_id = None
            else:
                raise NotImplementedError

            resource_class, resource_class_id = storage_plugin_manager.get_plugin_resource_class(
                resource.__class__.__module__,
                resource.__class__.__name__)

            id_tuple = resource.id_tuple()
            cleaned_id_items = []
            for t in id_tuple:
                if isinstance(t, BaseStorageResource):
                    cleaned_id_items.append(session.local_id_to_global_id[t._handle])
                else:
                    cleaned_id_items.append(t)
            import json
            id_str = json.dumps(tuple(cleaned_id_items))

            record, created = StorageResourceRecord.objects.get_or_create(
                resource_class_id = resource_class_id,
                storage_id_str = id_str,
                storage_id_scope_id = scope_id)
            session.local_id_to_global_id[resource._handle] = record.pk
            session.global_id_to_local_id[record.pk] = resource._handle

            if created:
                # Record a user-visible event
                log.debug("ResourceManager._persist_new_resource[%s] %s %s %s" % (session.scannable_id, created, record.pk, resource._handle))
                StorageResourceLearnEvent(severity = logging.INFO, storage_resource = record).save()

            creations[resource] = (record, created)

            # Add the new record to the index so that future records and resolve their
            # provide/subscribe relationships with respect to it
            self._subscriber_index.add_resource(record.pk, resource)

            self._class_index.add_record(record.pk, resource_class)

        attr_classes = set()
        for resource in ordered_for_creation:
            record, created = creations[resource]

            if isinstance(resource._meta.identifier, BaseGlobalId) and session.scannable_id != record.id:
                try:
                    record.reported_by.get(pk = session.scannable_id)
                except StorageResourceRecord.DoesNotExist:
                    log.debug("saw GlobalId resource %s from scope %s for the first time" % (record.id, session.scannable_id))
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

                updated = attr_model_class.objects.filter(
                    resource = record,
                    key = key).update(value = attr_model_class.encode(val))

                # If there was no existing record, create one
                if not updated:
                    attr_classes.add(attr_model_class)
                    if issubclass(attr_model_class, StorageResourceAttributeSerialized):
                        data = dict(
                            resource_id = record.id,
                            key = key,
                            value = attr_model_class.encode(val))

                    else:
                        data = dict(
                            resource_id = record.id,
                            key = key,
                            value_id = attr_model_class.encode(val))
                    attr_model_class.delayed.insert(data)

        for attr_model_class in attr_classes:
            attr_model_class.delayed.flush()

        for resource in ordered_for_creation:
            record, created = creations[resource]
            if created:
                # IMPORTANT: THIS TOTALLY RELIES ON SERIALIZATION OF ALL CREATION OPERATIONS
                # IN A SINGLE PROCESS INSTANCE OF THIS CLASS

                # This is a new resource which provides a field, see if any existing
                # resources would like to subscribe to it
                subscribers = self._subscriber_index.what_subscribes(resource)
                # Make myself a parent of anything that subscribes to me
                for s in subscribers:
                    log.info("Linked up me %s as parent of %s" % (record.pk, s))
                    self._edges.add_parent(s, record.pk)
                    s_record = StorageResourceRecord.objects.get(pk = s)
                    s_record.parents.add(record.pk)

                # This is a new resource which subscribes to a field, see if any existing
                # resource can provide it
                providers = self._subscriber_index.what_provides(resource)
                # Make my providers my parents
                for p in providers:
                    log.info("Linked up %s as parent of me, %s" % (p, record.pk))
                    self._edges.add_parent(record.pk, p)
                    record.parents.add(p)

        # Do a separate pass for parents so that we will have already
        # built the full local-to-global map
        for resource in resources:
            try:
                record, created = creations[resource]
            except KeyError:
                record = StorageResourceRecord.objects.get(pk = session.local_id_to_global_id[resource._handle])

            # Update self._edges
            for p in resource._parents:
                parent_global_id = session.local_id_to_global_id[p._handle]
                self._edges.add_parent(record.id, parent_global_id)

            new_parent_pks = [session.local_id_to_global_id[p._handle] for p in resource._parents]
            record.parents.add(*new_parent_pks)


resource_manager = ResourceManager()
