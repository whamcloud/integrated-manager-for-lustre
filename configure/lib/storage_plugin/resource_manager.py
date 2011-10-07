
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================


"""The resource manager is the home of the global view of the resources populated from
all plugins.  StoragePlugin instances have their own local caches of resources, which
they use to periodically update this central store.

Concurrency:
    This code is written for multi-threaded use within a single process.
    It is not safe to have multiple processes running plugins at this stage.
    We serialize operations from different plugins using a big lock, and 
    we use the autocommit decorator on persistence functions because
    otherwise we would have to explicitly commit at the start of
    each one to see changes from other threads.

WARNING:
    There is a globl instance of ResourceManager initialized in this module, and
    its initialization does a significant amount of DB activity.  Don't import
    this module unless you're really going to use it.
"""

from configure.lib.storage_plugin.log import storage_plugin_log as log
from configure.lib.storage_plugin.resource import ScannableId, GlobalId
from configure.lib.storage_plugin.manager import storage_plugin_manager

from django.db import transaction

from collections import defaultdict
import threading

class PluginSession(object):
    def __init__(self, scannable_id):
        self.local_id_to_global_id = {}
        self.scannable_id = scannable_id

class EdgeIndex(object):
    def __init__(self):
        # Define: Edges go 'from' child 'to' parent
        # Map of 'from' to (from,to)
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
            for k,v in self._parent_from_edge.items():
                v.remove(e)
            for k,v in self._parent_to_edge.items():
                v.remove(e)
        del self._parent_to_edge[node]
        del self._parent_from_edge[node]

    def populate(self):
        from configure.models import StorageResourceRecord
        from django.db.models import Q
        for srr in StorageResourceRecord.objects.filter(~Q(parents = None)).values('id', 'parents'):
            child = srr['id']
            parent = srr['parents']
            self.add_parent(child, parent)

class SubscriberIndex(object):
    def __init__(self):
        # Map (field_name, field_value) to list of resource global id
        self._subscribe_value_to_id = defaultdict(set)
        self._provide_value_to_id = defaultdict(set)

    def what_provides(self, field_name, field_value):
        return self._provide_value_to_id[(field_name, field_value)]

    def what_subscribes(self, field_name, field_value):
        return self._subscribe_value_to_id[(field_name, field_value)]

    def add_provider(self, resource_id, field_name, field_value):
        self._provide_value_to_id[(field_name, field_value)].add(resource_id)

    def remove_provider(self, resource_id, field_name, field_value):
        self._provide_value_to_id[(field_name, field_value)].remove(resource_id)

    def add_subscriber(self, resource_id, field_name, field_value):
        self._subscribe_value_to_id[(field_name, field_value)].add(resource_id)

    def remove_subscriber(self, resource_id, field_name, field_value):
        self._subscribe_value_to_id[(field_name, field_value)].remove(resource_id)

    def add_resource(self, resource_id, resource):
        for field_name in resource._provides:
            self.add_provider(resource_id, field_name, getattr(resource, field_name))
        for field_name in resource._subscribes:
            self.add_subscriber(resource_id, field_name, getattr(resource, field_name))

    def remove_resource(self, resource_id, resource):
        for field_name in resource._provides:
            self.remove_provider(resource_id, field_name, getattr(resource, field_name))
        for field_name in resource._subscribes:
            self.remove_subscriber(resource_id, field_name, getattr(resource, field_name))

    def populate(self):
        from configure.lib.storage_plugin import storage_plugin_manager
        from configure.models import StorageResourceAttribute
        # TODO: encapsulate retrieval in StorageResourceAttribute to hide encoding
        import json
        for resource_class_id, resource_class in storage_plugin_manager.get_all_resources():
            for p in resource_class._provides:
                instances = StorageResourceAttribute.objects.filter(
                        resource__resource_class = resource_class_id,
                        key = p).values('resource__id', 'value')
                for i in instances:
                    self.add_provider(i['resource__id'], p, json.loads(i['value']))

            for s in resource_class._subscribes:
                instances = StorageResourceAttribute.objects.filter(
                        resource__resource_class = resource_class_id,
                        key = s).values('resource__id', 'value')
                for i in instances:
                    self.add_subscriber(i['resource__id'], s, json.loads(i['value']))

class ResourceManager(object):
    def __init__(self):
        self._sessions = {}
        self._instance_lock = threading.Lock()

        # Map of (resource_global_id, alert_class) to AlertState pk
        self._active_alerts = {}
        
        # In-memory bidirectional lookup table of resource parent-child relationships
        self._edges = EdgeIndex()
        self._edges.populate()

        # In-memory lookup table of 'provide' and 'subscribe' resource attributes
        self._subscriber_index = SubscriberIndex()
        self._subscriber_index.populate()

    def session_open(self, scannable_id, scannable_local_id, initial_resources):
        log.info(">> session_open %s" % scannable_id)
        with self._instance_lock:
            if scannable_id in self._sessions:
                log.warning("Clearing out old session for scannable ID %s" % scannable_id)
                del self._sessions[scannable_id]

            session = PluginSession(scannable_id)
            #session.local_id_to_global_id[scannable_local_id] = scannable_id
            self._sessions[scannable_id] = session
            self._persist_new_resources(session, initial_resources)
            
            # TODO: cull any resources which are in the database with
            # ScannableIds for this scannable but not in the initial
            # resource list

            # Special case for the built in 'linux' plugin: hook up resources
            # to Lun and LunNode objects to interface with the world of Lustre
            # TODO: don't just do this at creation, do updates too
            from linux import HydraHostProxy
            from configure.lib.storage_plugin import storage_plugin_manager
            from configure.lib.storage_plugin import ResourceQuery
            from configure.lib.storage_plugin import base_resources
            from monitor.models import Lun, LunNode, Host
            scannable_resource = ResourceQuery().get_resource(scannable_id)
            if isinstance(scannable_resource, HydraHostProxy):
                # TODO: restrict below searches to only this scannable ID to 
                # avoid rescanning everything every time
                host = Host.objects.get(pk = scannable_resource.host_id)

                def lun_get_or_create(resource_id):
                    try:
                        return Lun.objects.get(storage_resource_id = resource_id)
                    except Lun.DoesNotExist:
                        shared = True
                        # TODO: work out whether shared by finding the furthest
                        # LogicalDrive ancestor and seeing if its a ScsiDevice
                        # or an UnsharedDevice
                        r = ResourceQuery().get_resource(resource_id)
                        lun = Lun.objects.create(
                                size = r.size,
                                storage_resource_id = r._handle)

                        return lun

                # Update LunNode objects for DeviceNodes
                node_types = []
                # FIXME: mechanism to get subclasses of base_resources.DeviceNode
                node_types.append(storage_plugin_manager.get_plugin_resource_class_id('linux', 'ScsiDeviceNode'))
                node_types.append(storage_plugin_manager.get_plugin_resource_class_id('linux', 'UnsharedDeviceNode'))
                node_types.append(storage_plugin_manager.get_plugin_resource_class_id('linux', 'LvmDeviceNode'))
                node_types.append(storage_plugin_manager.get_plugin_resource_class_id('linux', 'PartitionDeviceNode'))
                node_types.append(storage_plugin_manager.get_plugin_resource_class_id('linux', 'MultipathDeviceNode'))
                node_resources = ResourceQuery().get_class_resources(node_types, storage_id_scope = scannable_id)
                for r in node_resources:
                    # A node which has children is already in use
                    # (it might contain partitions, be an LVM PV, be in 
                    #  use by a local filesystem, or as swap)
                    if ResourceQuery().record_has_children(r._handle):
                        continue

                    device = ResourceQuery().record_find_parent(r._handle, base_resources.LogicalDrive)
                    if device == None:
                        raise RuntimeError("Got a device node resource %s with no LogicalDrive ancestor!" % r._handle)

                    lun = lun_get_or_create(device)
                    try:
                        lun_node = LunNode.objects.get(
                                host = host,
                                path = r.path)
                        if not lun_node.storage_resource_id:
                            lun_node.storage_resource_id = r._handle
                            lun_node.save()

                    except LunNode.DoesNotExist:
                        lun_node = LunNode.objects.create(
                            lun = lun,
                            host = host,
                            path = r.path,
                            storage_resource_id = r._handle)
        log.info("<< session_open %s" % scannable_id)

    def session_update_resource(self, scannable_id, local_resource_id, attrs):
        with self._instance_lock:
            session = self._sessions[scannable_id]
            record_pk = session.local_id_to_global_id[local_resource_id]

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
            # TODO: potentially orphaning resources, find and cull them

    def session_update_stat(self, scannable_id, local_resource_id, update_data):
        # Note: intentionally lock-free, to be called synchronously during
        # plugin execution (pass stats straight through rather than
        # messing with them)

        #XXX How safe is this really to be run without the _instance_lock, 
        # as we're reading out of _sessions and local_id_to...
        session = self._sessions[scannable_id]
        record_pk = session.local_id_to_global_id[local_resource_id]
        from configure.models import StorageResourceRecord
        record = StorageResourceRecord.objects.get(pk = record_pk)
        from monitor.metrics import VendorMetricStore
        from django.db import transaction
        # TODO: per-plugin update period
        metric_store = VendorMetricStore(record, 5)
        metric_store.update(update_data)

        #import time
        #import datetime
        #t = int(time.time()) - 60

        #print "Last minute since %s" % datetime.datetime.now()
        #print ">>"
        #points = metric_store.fetch('Average', start_time = t)
        #ts_list = points.keys()
        #ts_list.sort()
        #for ts in ts_list:
        #    vals = points[ts]
        #    print time.ctime(ts), vals['test_stat']
        #print "<<"
        #print ""

    @transaction.autocommit
    def _resource_modify_parent(self, record_pk, parent_pk, remove):
        from configure.models import StorageResourceRecord
        record = StorageResourceRecord.objects.get(pk = record_pk)
        if remove:
            record.parents.remove(parent_pk)
        else:
            record.parents.add(parent_pk)

    @transaction.autocommit
    def _resource_persist_update_attributes(self, record_pk, attrs):
        from configure.models import StorageResourceRecord
        record = StorageResourceRecord.objects.get(record_pk)
        record.update_attributes(attrs)

    def session_add_resources(self, scannable_id, resources):
        """NB this is plural because new resources may be interdependent
        and if so they must be added in a blob so that we can hook up the 
        parent relationships"""
        with self._instance_lock:
            self._persist_new_resources(self._sessions[scannable_id])

    def session_remove_resources(self, scannable_id, resources):
        with self._instance_lock:
            # TODO: remove these resources (unless some other resources
            # are still referring to them)
            #self._edges.remove_node(
            pass

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
        from configure.models import StorageAlertPropagated
        record_global_pk = alert_state.alert_item_id
        descendents = self._get_descendents(record_global_pk)
        if len(descendents) == 0:
            print "Global resource ID %s has no descendents" % record_global_pk
        for d in descendents:
            sap, created = StorageAlertPropagated.objects.get_or_create(
                    storage_resource_id = d,
                    alert_state = alert_state)

    def _persist_alert_unpropagate(self, alert_state):
        from configure.models import StorageAlertPropagated
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
        from configure.models import StorageResourceRecord
        from configure.models import StorageResourceAlert
        record = StorageResourceRecord.objects.get(pk = record_pk)
        alert_state = StorageResourceAlert.notify(record, active, alert_class=alert_class, attribute=attribute)
        return alert_state

    @transaction.autocommit
    def _persist_new_resources(self, session, resources):
        from configure.models import StorageResourceRecord

        record_cache = {}
        for r in resources:
            if r._handle in session.local_id_to_global_id:
                raise RuntimeError("Session tried to add resource twice")

            if isinstance(r.identifier, ScannableId):
                scope_id = session.scannable_id
            elif isinstance(r.identifier, GlobalId):
                scope_id = None
            else:
                raise NotImplementedError

            resource_class_id = storage_plugin_manager.get_plugin_resource_class_id(
                    r.__class__.__module__,
                    r.__class__.__name__)

            record, created = StorageResourceRecord.objects.get_or_create(
                    resource_class_id = resource_class_id,
                    storage_id_str = r.id_str(),
                    storage_id_scope_id = scope_id)
            if created:
                #log.debug("Created SRR %s (class %s id %s scope %s)" % (record.pk,
                #    r.__class__.__name__, r.id_str(), scope_id))
                from configure.models import StorageResourceLearnEvent
                import logging
                # Record a user-visible event
                StorageResourceLearnEvent(severity = logging.INFO, storage_resource = record).save()
                
                # IMPORTANT: THIS TOTALLY RELIES ON SERIALIZATION OF ALL CREATION OPERATIONS
                # IN A SINGLE PROCESS INSTANCE OF THIS CLASS

                # This is a new resource which provides a field, see if any existing
                # resources would like to subscribe to it
                if r._provides:
                    subscribers = self._subscriber_index.what_subscribes(sub_field, getattr(r, sub_field))
                    # Make myself a parent of anything that subscribes to me
                    for s in subscribers:
                        self._edges.add_parent(s, record.pk)
                        s_record = StorageResourceRecord.objects.get(pk = s)
                        s_record.parents.add(record.pk)

                # This is a new resource which subscribes to a field, see if any existing
                # resource can provide it
                for sub_field in r._subscribes:
                    providers = self._subscriber_index.what_provides(sub_field, getattr(r, sub_field))
                    # Make my providers my parents
                    for p in providers:
                        self._edges.add_parent(record.pk, p)
                        record.parents.add(p)

                # Add the new record to the index so that future records and resolve their
                # provide/subscribe relationships with respect to it
                self._subscriber_index.add_resource(record.pk, r)

            else:
                #log.debug("Loaded existing SRR %s (class %s id %s scope %s)" % (record.pk,
                #    r.__class__.__name__, r.id_str(), scope_id))
                pass
            session.local_id_to_global_id[r._handle] = record.pk
            self._resource_persist_attributes(r, record)
            record_cache[record.pk] = record

        # Do a separate pass for parents so that we will have already
        # built the full local-to-global map
        for r in resources:
            resource_global_id = session.local_id_to_global_id[r._handle]

            # Update self._edges
            for p in r._parents:
                parent_global_id = session.local_id_to_global_id[p._handle]
                self._edges.add_parent(resource_global_id, parent_global_id)

            # Update the database
            record = record_cache[resource_global_id]
            self._resource_persist_parents(r, session, record)

    @transaction.autocommit
    def _resource_persist_attributes(self, resource, record):
        record.update_attributes(resource._storage_dict)

    @transaction.autocommit
    def _resource_persist_parents(self, resource, session, record):
        from configure.models import StorageResourceRecord

        new_parent_pks = [session.local_id_to_global_id[p._handle] for p in resource._parents]
        existing_parents = record.parents.all()

        # TODO: work out how to cull relationships
        # (can't just do it here because persist_parents is called with a LOCAL resource
        # which may not have all the parents)
        #for ep in existing_parents:
        #    if not ep.pk in new_parent_pks:
        #        record.parents.remove(ep)

        existing_parent_handles = [ep.pk for ep in existing_parents]
        for pk in new_parent_pks:
            if not pk in existing_parent_handles:
                record.parents.add(pk)

resource_manager = ResourceManager()
