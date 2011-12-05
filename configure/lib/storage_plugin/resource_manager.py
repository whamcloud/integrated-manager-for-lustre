
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
    def __init__(self, scannable_id, update_period):
        self.local_id_to_global_id = {}
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
            for k, v in self._parent_from_edge.items():
                v.remove(e)
            for k, v in self._parent_to_edge.items():
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

    def add_resource(self, resource_id, resource = None):
        if not resource:
            from configure.models import StorageResourceRecord
            resource = StorageResourceRecord.objects.get(pk = resource_id).to_resource()

        for field_name, key in resource._provides:
            self.add_provider(resource_id, key, getattr(resource, field_name))
        for field_name, key in resource._subscribes:
            self.add_subscriber(resource_id, key, getattr(resource, field_name))

    def remove_resource(self, resource_id, resource = None):
        if not resource:
            from configure.models import StorageResourceRecord
            resource = StorageResourceRecord.objects.get(pk = resource_id).to_resource()

        for field_name, key in resource._provides:
            self.remove_provider(resource_id, key, getattr(resource, field_name))
        for field_name, key in resource._subscribes:
            self.remove_subscriber(resource_id, key, getattr(resource, field_name))

    def populate(self):
        from configure.models import StorageResourceAttribute
        for resource_class_id, resource_class in storage_plugin_manager.get_all_resources():

            for p_attr, p_key in resource_class._provides:
                instances = StorageResourceAttribute.objects.filter(
                        resource__resource_class = resource_class_id,
                        key = p_attr).values('resource__id', 'value')
                attribute_object = resource_class._storage_attributes[p_attr]
                for i in instances:
                    self.add_provider(i['resource__id'], p_key, attribute_object.decode(i['value']))

            for s_attr, s_key in resource_class._subscribes:
                instances = StorageResourceAttribute.objects.filter(
                        resource__resource_class = resource_class_id,
                        key = s_attr).values('resource__id', 'value')
                attribute_object = resource_class._storage_attributes[s_attr]
                for i in instances:
                    self.add_subscriber(i['resource__id'], s_key, attribute_object.decode(i['value']))


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

    def session_open(self,
            scannable_id,
            scannable_local_id,
            initial_resources,
            update_period):
        log.debug(">> session_open %s (%s resources)" % (scannable_id, len(initial_resources)))
        with self._instance_lock:
            if scannable_id in self._sessions:
                log.warning("Clearing out old session for scannable ID %s" % scannable_id)
                del self._sessions[scannable_id]

            session = PluginSession(scannable_id, update_period)
            #session.local_id_to_global_id[scannable_local_id] = scannable_id
            self._sessions[scannable_id] = session
            self._persist_new_resources(session, initial_resources)
            self._cull_lost_resources(session, initial_resources)

            # TODO: cull any resources which are in the database with
            # ScannableIds for this scannable but not in the initial
            # resource list

            # Special case for the built in 'linux' plugin: hook up resources
            # to Lun and LunNode objects to interface with the world of Lustre
            # TODO: don't just do this at creation, do updates too
            from linux import HydraHostProxy
            from configure.lib.storage_plugin.query import ResourceQuery
            scannable_resource = ResourceQuery().get_resource(scannable_id)
            if isinstance(scannable_resource, HydraHostProxy):
                self._persist_lun_updates(scannable_id, scannable_resource)

            # Plugins are allowed to create HydraHostProxy objects, indicating that
            # we should created a ManagedHost to go with it (e.g. discovering VMs)
            self._persist_created_hosts(session, scannable_id)

        log.debug("<< session_open %s" % scannable_id)

    def session_close(self, scannable_id):
        with self._instance_lock:
            try:
                del self._sessions[scannable_id]
            except KeyError:
                log.warning("Cannot remove session for %s, it does not exist" % scannable_id)

    @transaction.commit_on_success
    def _persist_created_hosts(self, session, scannable_id):
        log.debug("_persist_created_hosts")

        # FIXME: look up more efficiently (don't currently keep an in-memory record of the
        # class of each resource)
        def get_session_resources_of_type(session, klass):
            for record_pk in session.local_id_to_global_id.values():
                from configure.models import StorageResourceRecord
                record = StorageResourceRecord.objects.get(pk = record_pk)
                resource = record.to_resource()
                if isinstance(resource, klass):
                    yield (record, resource)

        from configure.lib.storage_plugin import builtin_resources
        for record, resource in get_session_resources_of_type(session, builtin_resources.VirtualMachine):
            if not resource.host_id:
                from configure.models import ManagedHost
                log.info("Creating host for new VirtualMachine resource: %s" % resource.address)
                host = ManagedHost.create_from_string(
                        resource.address,
                        virtual_machine = record.pk)
                record.update_attribute('host_id', host.pk)

                # NB any instances of this resource within the plugin session
                # that reported it won't see the change to host_id attribute, but that's
                # fine, they have no right to know.

    @transaction.commit_on_success
    def _persist_lun_updates(self, scannable_id, scannable_resource):
        from configure.lib.storage_plugin.query import ResourceQuery
        from configure.lib.storage_plugin import builtin_resources
        from configure.models import Lun, LunNode, ManagedHost

        def lun_get_or_create(resource_id):
            try:
                return Lun.objects.get(storage_resource = resource_id)
            except Lun.DoesNotExist:
                # Determine whether a device is shareable by whether it has a SCSI
                # ancestor (e.g. an LV on a scsi device is shareable, an LV on an IDE
                # device is not)
                from linux import ScsiDevice
                scsi_ancestor = ResourceQuery().record_find_ancestors(resource_id, ScsiDevice)
                shareable = (scsi_ancestor != None)
                r = ResourceQuery().get_resource(resource_id)
                lun = Lun.objects.create(
                        size = r.size,
                        storage_resource_id = r._handle,
                        shareable = shareable)
                return lun

        # Update LunNode objects for DeviceNodes
        node_types = []
        # FIXME: mechanism to get subclasses of builtin_resources.DeviceNode
        node_types.append(storage_plugin_manager.get_plugin_resource_class('linux', 'ScsiDeviceNode')[1])
        node_types.append(storage_plugin_manager.get_plugin_resource_class('linux', 'UnsharedDeviceNode')[1])
        node_types.append(storage_plugin_manager.get_plugin_resource_class('linux', 'LvmDeviceNode')[1])
        node_types.append(storage_plugin_manager.get_plugin_resource_class('linux', 'PartitionDeviceNode')[1])
        node_types.append(storage_plugin_manager.get_plugin_resource_class('linux', 'MultipathDeviceNode')[1])
        node_resources = ResourceQuery().get_class_resources(node_types, storage_id_scope = scannable_id)
        host = ManagedHost.objects.get(pk = scannable_resource.host_id)
        touched_luns = set()
        touched_lun_nodes = set()
        for record in node_resources:
            r = record.to_resource()
            # A node which has children is already in use
            # (it might contain partitions, be an LVM PV, be in
            #  use by a local filesystem, or as swap)
            if ResourceQuery().record_has_children(r._handle):
                continue

            device = ResourceQuery().record_find_ancestor(record.pk, builtin_resources.LogicalDrive)
            if device == None:
                log.error("Got a device node resource %s with no LogicalDrive ancestor!" % r._handle)
                continue
                #raise RuntimeError("Got a device node resource %s with no LogicalDrive ancestor!" % r._handle)

            lun = lun_get_or_create(device)
            try:
                lun_node = LunNode.objects.get(
                        host = host,
                        path = r.path)
                if not lun_node.storage_resource:
                    lun_node.storage_resource_id = record.pk
                    lun_node.save()

            except LunNode.DoesNotExist:
                # If setting up a non-shareable device, make its first
                # LunNode a primary
                if not lun.shareable:
                    primary = True
                    use = True
                else:
                    primary = False
                    use = False

                # FIXME: assumes that we discover the device nodes AFTER the underlying storage,
                # in order that the underlying VDs will be here when we look for home
                # controller information.  This is true for controller-hosted virtual machines,
                # as we set up the VMs after scanning the controller for the first time, but
                # it is not true in the general case.

                from configure.models import StorageResourceRecord
                ancestor_virtual_disks = ResourceQuery().record_find_ancestors(
                        record.pk, builtin_resources.VirtualDisk)
                # collect home controller information
                vd_home_controllers = set()
                for vd_id in ancestor_virtual_disks:
                    vd_res = StorageResourceRecord.objects.get(pk = vd_id).to_resource()
                    if vd_res.home_controller:
                        vd_home_controller_pk = vd_res.home_controller._handle
                        vd_home_controllers.add(vd_home_controller_pk)

                host_proxy = StorageResourceRecord.objects.get(pk = scannable_id).to_resource()
                if len(vd_home_controllers) == 1 and host_proxy.virtual_machine:
                    # We can identify a primary host if there is one home controller
                    # for all underlying VDs
                    vd_home_controller_id = vd_home_controllers.pop()
                    host_home_controller_id = host_proxy.virtual_machine.home_controller._handle
                    if host_home_controller_id == vd_home_controller_id:
                        primary = True
                        use = True
                        log.info("Device %s on same host controller as host %s, marking primary" % (device, host))
                    else:
                        # In this case, there is enough information that we will have found
                        # the primary mount elsewhere, and this is a potential secondary mount.

                        # FIXME: first-come-first-served assignment of secondary works
                        # when the LUN is only presented to two hosts, but not in the general
                        # case: need more advanced ALUA detection to do this right (but this
                        # works well enough for a controlled 10KE environment)
                        use = True
                        primary = False
                        log.info("Device %s (hc %s) has different home controller than host %s (hc %s)" % (device, vd_home_controller_id, host, host_home_controller_id))
                else:
                    log.info("Device %s on %s home controllers, host %s virtual machine='%s', cannot infer primary mount " % (device, len(vd_home_controllers), host, host_proxy.virtual_machine))
                    # The host does not have a home controller, or the underlying VDs don't
                    # all point to the same host controller, or don't have a host controller
                    # set: we can't guess at the primary

                    # A hack to provide some arbitrary primary/secondary assignments
                    import settings
                    if settings.PRIMARY_LUN_HACK:
                        if lun.lunnode_set.count() == 0:
                            primary = True
                            use = True
                        else:
                            primary = False
                            if lun.lunnode_set.filter(use = True).count() > 1:
                                use = False
                            else:
                                use = True
                    else:
                        use = False
                        primary = False

                lun_node = LunNode.objects.create(
                    lun = lun,
                    host = host,
                    path = r.path,
                    storage_resource_id = record.pk,
                    primary = primary,
                    use = use)

            touched_luns.add(lun_node.pk)
            touched_lun_nodes.add(lun_node.pk)
            # BUG: when mjmac set up on IU, it saw mpath devices fine as
            # LunNodes.  But when he created some CLVM LVs on multipath
            # devices, the multipath devices stayed (see TODO below) AND
            # the new LV devices didn't appear.  Why didn't they get promoted
            # to LunNodes?  they were in hydra-agent output
            # TODO: cope with CLVM where device nodes appear and disappear
            # - simplest thing would be to have the agent lie and claim
            # that the device node is always there (based on LV presence
            # in 'lvs' output.  But that's a hack.  And appearing in 'lvs'
            # just means the PVs are on shared storage that the host has
            # access to, not necessarily that the host is in the pacemaker
            # group that will access the LVs.

        # TODO: do this checking on create/remove/link operations too
        for lun_node in LunNode.objects.filter(host = host):
            if not lun_node.pk in touched_lun_nodes:
                lun = lun_node.lun
                from configure.models import ManagedTargetMount
                if ManagedTargetMount.objects.filter(block_device = lun_node).count() == 0:
                    log.info("Removing LunNode %s" % lun_node)
                    lun_node.delete()
                    if lun.lunnode_set.count() == 0:
                        log.info("Removing Lun %s" % lun_node)
                        lun.delete()
                    else:
                        log.info("Keeping Lun %s, reffed by another LunNode" % lun_node)

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
            # TODO: potentially orphaning resources, find and cull them

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
        from configure.models import StorageResourceRecord, StorageResourceStatistic
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
            from r3d.exceptions import BadUpdateString
            try:
                stat_record.update(stat_name, stat_properties, stat_data)
            except BadUpdateString:
                # FIXME: Initial insert usually fails because r3d isn't getting
                # its start time from the first insert time
                pass

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
            self._persist_new_resources(self._sessions[scannable_id], resources)

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
    def _cull_lost_resources(self, session, reported_resources):
        reported_global_ids = []
        for r in reported_resources:
            if isinstance(r.identifier, ScannableId):
                reported_global_ids.append(session.local_id_to_global_id[r._handle])

        from configure.models import StorageResourceRecord
        from django.db.models import Q
        lost_resources = StorageResourceRecord.objects.filter(
                ~Q(pk__in = reported_global_ids),
                storage_id_scope = session.scannable_id)
        for r in lost_resources:
            self._cull_resource(r)

    def _cull_resource(self, resource_record):
        log.info("Culling resource '%s'" % resource_record.pk)
        from configure.models import StorageResourceRecord

        for dependent in StorageResourceRecord.objects.filter(
                parents = resource_record):
            dependent.parents.remove(resource_record)

        # TODO: find ResourceReference attributes on other objects
        # that refer to this one and unhook them or if they're non-optional
        # then delete that resource

        # TODO: find where lustre target objects or host objects hold a reference
        # to this resource

        self._subscriber_index.remove_resource(resource_record.pk)
        resource_record.delete()

    def global_remove_resource(self, resource_id):
        with self._instance_lock:
            # Ensure that no open sessions are holding a reference to this ID
            from configure.models import StorageResourceRecord
            try:
                record = StorageResourceRecord.objects.get(pk = resource_id)
            except StorageResourceRecord.DoesNotExist:
                log.error("ResourceManager received invalid request to remove non-existent resource %s" % resource_id)
                return

            resource = record.to_resource()
            from configure.lib.storage_plugin.resource import ScannableResource
            if isinstance(resource, ScannableResource):
                scoped_resources = StorageResourceRecord.objects.filter(
                    storage_id_scope = resource_id)
                for r in scoped_resources:
                    self._cull_resource(r)

            self._cull_resource(record)

            # TODO: deal with GlobalId resources that get left behind, like SCSI IDs,
            # LVM VGs and LVs.  Could look for islands of GlobalId resources with no
            # relationships to ScannableResources, but that could falsely remove some
            # things still existing: e.g. what if a host was just only reporting LVM
            # things?  they wouldn't have any parents.  Probably the more robust way to
            # do this is to track which scannables have had sessions which reported
            # a given GlobalId resource, and treat that like a reference count

    def _persist_new_resource(self, session, resource):
        from configure.models import StorageResourceRecord

        if resource._handle_global:
            # Bit of a weird one: this covers the case where a plugin sessoin
            # was given a root resource that had some ResourceReference attributes
            # that pointed to resources from a different plugin
            return

        if resource._handle in session.local_id_to_global_id:
            return

        if isinstance(resource.identifier, ScannableId):
            scope_id = session.scannable_id
        elif isinstance(resource.identifier, GlobalId):
            scope_id = None
        else:
            raise NotImplementedError

        resource_class, resource_class_id = storage_plugin_manager.get_plugin_resource_class(
                resource.__class__.__module__,
                resource.__class__.__name__)

        # Find any ResourceReference attributes and persist them first so that
        # we know their global IDs for serializing this one
        for key, value in resource._storage_dict.items():
            # Special case for ResourceReference attributes, because the resource
            # object passed from the plugin won't have a global ID for the referenced
            # resource -- we have to do the lookup inside ResourceManager
            attribute_obj = resource_class.get_attribute_properties(key)
            from configure.lib.storage_plugin import attributes
            if isinstance(attribute_obj, attributes.ResourceReference):
                if value:
                    referenced_resource = value
                    if not referenced_resource._handle_global:
                        if not referenced_resource._handle in session.local_id_to_global_id:
                            self._persist_new_resource(session, referenced_resource)
                            assert referenced_resource._handle in session.local_id_to_global_id

        id_tuple = resource.id_tuple()
        cleaned_id_items = []
        for t in id_tuple:
            from configure.lib.storage_plugin.resource import StorageResource
            if isinstance(t, StorageResource):
                cleaned_id_items.append(session.local_id_to_global_id[t._handle])
            else:
                cleaned_id_items.append(t)
        import json
        id_str = json.dumps(tuple(cleaned_id_items))

        record, created = StorageResourceRecord.objects.get_or_create(
                resource_class_id = resource_class_id,
                storage_id_str = id_str,
                storage_id_scope_id = scope_id)
        if created:
            from configure.models import StorageResourceLearnEvent
            import logging
            # Record a user-visible event
            StorageResourceLearnEvent(severity = logging.INFO, storage_resource = record).save()

            # IMPORTANT: THIS TOTALLY RELIES ON SERIALIZATION OF ALL CREATION OPERATIONS
            # IN A SINGLE PROCESS INSTANCE OF THIS CLASS

            # This is a new resource which provides a field, see if any existing
            # resources would like to subscribe to it
            for prov_field, prov_key in resource._provides:
                subscribers = self._subscriber_index.what_subscribes(prov_key, getattr(resource, prov_field))
                # Make myself a parent of anything that subscribes to me
                for s in subscribers:
                    log.info("Linked up me %s as parent of %s" % (record.pk, s))
                    self._edges.add_parent(s, record.pk)
                    s_record = StorageResourceRecord.objects.get(pk = s)
                    s_record.parents.add(record.pk)

            # This is a new resource which subscribes to a field, see if any existing
            # resource can provide it
            for sub_field, sub_key in resource._subscribes:
                providers = self._subscriber_index.what_provides(sub_key, getattr(resource, sub_field))
                # Make my providers my parents
                for p in providers:
                    log.info("Linked up %s as parent of me, %s" % (p, record.pk))
                    self._edges.add_parent(record.pk, p)
                    record.parents.add(p)

            # Add the new record to the index so that future records and resolve their
            # provide/subscribe relationships with respect to it
            self._subscriber_index.add_resource(record.pk, resource)

        session.local_id_to_global_id[resource._handle] = record.pk
        self._resource_persist_attributes(session, resource, record)

        if created:
            log.debug("persist_new_resource[%s] %s %s %s" % (session.scannable_id, created, record.pk, resource._handle))
        return record

    # Use commit on success to avoid situations where a resource record
    # lands in the DB without its attribute records.
    # FIXME: there are cases where _persist_new_resource gets called outside
    # of _persist_new_resources, make sure it's wrapped in a transaction too
    @transaction.commit_on_success
    def _persist_new_resources(self, session, resources):
        for r in resources:
            self._persist_new_resource(session, r)

        # Do a separate pass for parents so that we will have already
        # built the full local-to-global map
        for r in resources:
            resource_global_id = session.local_id_to_global_id[r._handle]

            # Update self._edges
            for p in r._parents:
                parent_global_id = session.local_id_to_global_id[p._handle]
                self._edges.add_parent(resource_global_id, parent_global_id)

            # Update the database
            # FIXME: shouldn't need to SELECT the record to set up its relationships
            from configure.models import StorageResourceRecord
            record = StorageResourceRecord.objects.get(pk = resource_global_id)
            self._resource_persist_parents(r, session, record)

    @transaction.autocommit
    def _resource_persist_attributes(self, session, resource, record):
        from configure.models import StorageResourceAttribute
        # TODO: remove existing attrs not in storage_dict
        resource_class = storage_plugin_manager.get_resource_class_by_id(record.resource_class_id)

        for key, value in resource._storage_dict.items():
            # Special case for ResourceReference attributes, because the resource
            # object passed from the plugin won't have a global ID for the referenced
            # resource -- we have to do the lookup inside ResourceManager
            attribute_obj = resource_class.get_attribute_properties(key)
            from configure.lib.storage_plugin import attributes
            if isinstance(attribute_obj, attributes.ResourceReference):
                if value and not value._handle_global:
                    value = session.local_id_to_global_id[value._handle]
                elif value and value._handle_global:
                    value = value._handle
            try:
                existing = StorageResourceAttribute.objects.get(resource = record, key = key)
                encoded_val = resource_class.encode(key, value)
                if existing.value != encoded_val:
                    existing.value = encoded_val
                    existing.save()
            except StorageResourceAttribute.DoesNotExist:
                attr = StorageResourceAttribute(
                        resource = record, key = key,
                        value = resource_class.encode(key, value))
                attr.save()

    @transaction.autocommit
    def _resource_persist_parents(self, resource, session, record):
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
