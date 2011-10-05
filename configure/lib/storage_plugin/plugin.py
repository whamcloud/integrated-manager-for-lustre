
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

import settings
from collections import defaultdict
from django.db import transaction

from configure.lib.storage_plugin.resource import StorageResource, ScannableId, GlobalId
from configure.lib.storage_plugin.log import storage_plugin_log

import threading

class ResourceNotFound(Exception):
    pass

class ResourceIndex(object):
    def __init__(self, scannable_id):
        # Map (local_id) to resource
        self._local_id_to_resource = {}

        # Map (id_str, klass) to resource
        self._resource_id_to_resource = {}

    def add(self, resource):
        self._local_id_to_resource[resource._handle] = resource
        resource.id_str()

        # Why don't we need a scope resource in here?
        # Because if it's a ScannableId then only items for that
        # scannable will be in this ResourceIndex (index is per
        # plugin instance), and if it's a GlobalId then it doesn't
        # have a scope.
        resource_id = (resource.id_str(), resource.__class__)
        if resource_id in self._resource_id_to_resource:
            raise RuntimeError("Duplicate resource added to index")
        self._resource_id_to_resource[resource_id] = resource

    def get(self, klass, **attrs):
        id_str = klass(**attrs).id_str()
        try:
            return self._resource_id_to_resource[(id_str, klass)]
        except KeyError:
            raise ResourceNotFound()

    def all(self):
        return self._local_id_to_resource.values()

class StoragePlugin(object):
    def generate_handle(self):
        with self._handle_lock:
            self._handle_counter += 1
            handle = self._handle_counter
            return handle

    def __init__(self, scannable_id = None):
        from configure.lib.storage_plugin import storage_plugin_manager
        self._handle = storage_plugin_manager.register_plugin(self)

        self._handle_lock = threading.Lock()
        self._instance_lock = threading.Lock()
        self._handle_counter = 0

        self._index = ResourceIndex(scannable_id)
        self._scannable_id = scannable_id

        self._resource_lock = threading.Lock()
        self._delta_new_resources = []
        self._delta_delete_resources = []

        # TODO: give each one its own log, or at least a prefix
        self.log = storage_plugin_log

        self._alerts_lock = threading.Lock()
        self._delta_alerts = set()
        self._alerts = {}

    def initial_scan(self, root_resource):
        """To be implemented by subclasses.  Identify all resources
           present at this time and call register_resource on them.
           
           Any plugin which throws an exception from here is assumed
           to be broken - this will not be retried.  If one of your
           controllers is not contactable, you must handle that and 
           when it comes back up let us know during an update call."""
        raise NotImplementedError

    def update_scan(self, root_resource):
        """Optionally implemented by subclasses.  Perform any required
           periodic refresh of data and update any resource instances"""
        pass


    def _flush_alerts(self):
        from configure.lib.storage_plugin.resource_manager import resource_manager 
        with self._alerts_lock:
            for (resource,attribute,alert_class) in self._delta_alerts:
                # FIXME: risk of a resource still being here that's since been deleted
                # from the local index.  Could just do this inside _resource_lock?
                active = self._alerts[(resource,attribute,alert_class)]
                resource_manager.session_notify_alert(
                        self._scannable_id, resource._handle,
                        active, alert_class, attribute)
            self._delta_alerts.clear()

    # commit_on_success is important here and in update_scan, because
    # if someone is registering a resource with parents
    # and something goes wrong, we must not accidently
    # leave it without parents, as that would cause the
    # it to incorrectly be considered a 'root' resource
    @transaction.commit_on_success
    def do_initial_scan(self, root_resource):
        from configure.lib.storage_plugin.resource_manager import resource_manager 
        root_resource._handle = self.generate_handle()

        self.initial_scan(root_resource)

        resource_manager.session_open(self._scannable_id, root_resource._handle, self._index.all())
        self._delta_new_resources = []

        for resource in self._index.all():
            # Check if any AlertConditions are matched
            for name,ac in resource._alert_conditions.items():
                alert_list = ac.test(resource)
                for name, attribute, active in alert_list:
                    self.notify_alert(active, resource, name, attribute)

        self._flush_alerts()

    @transaction.commit_on_success
    def do_periodic_update(self, root_resource):
        from configure.lib.storage_plugin.resource_manager import resource_manager 
        self.update_scan(root_resource)

        # Resources created since last update
        with self._resource_lock:
            if len(self._delta_new_resources) > 0:
                resource_manager.session_add_resources(self._scannable_id, self._delta_new_resources)
            self._delta_new_resources = []

            # Resources deleted since last update
            if len(self._delta_delete_resources) > 0:
                resource_manager.session_add_resources(self._scannable_id, self._delta_delete_resources)
            self._delta_delete_resources = []

            # Resources with changed attributes
            for resource in self._index.all():
                deltas = resource.flush_deltas()
                # If there were changes to attributes
                if len(deltas['attributes']) > 0:
                    resource_manager.session_update_resource(
                            self._scannable_id, resource._handle, deltas['attributes']) 

                    # Check if any AlertConditions are matched
                    for name,ac in resource._alert_conditions.items():
                        alert_list = ac.test(resource)
                        for name, attribute, active in alert_list:
                            self.notify_alert(active, resource, name, attribute)

                # If there were parents added or removed
                if len(deltas['parents']) > 0:
                    for parent_resource in deltas['parents']:
                        if parent_resource in resource._parents:
                            # If it's in the parents of the resource then it's an add
                            resource_manager.session_resource_add_parent(
                                    self._scannable_id, resource._handle,
                                    parent_resource._handle)
                        else:
                            # Else if's a remove
                            resource_manager.session_resource_remove_parent(
                                    self._scannable_id, resource._handle,
                                    parent_resource._handle)

        self._flush_alerts()

    def update_or_create(self, klass, parents = [], **attrs):
        with self._resource_lock:
            try:
                existing = self._index.get(klass, **attrs)
                for k,v in attrs.items():
                    setattr(existing, k, v)
                for p in parents:
                    existing.add_parent(p)
                return existing, False
            except ResourceNotFound:
                resource = klass(**attrs)
                for p in parents:
                    resource.add_parent(p)
                self._register_resource(resource)
                return resource, True

    def unregister_resource(self, resource):
        """Note: this does not immediately unregister the resource, rather marks it
        for removal at the next periodic update"""
        with self._resource_lock:
            pass
        # TODO: remove this resource from indices
        # and add it to the _delta_delete_resource list

    def notify_alert(self, active, resource, alert_name, attribute = None):
        # This will be flushed through to the database by update_scan
        key = (resource,attribute,alert_name)
        value = active
        with self._alerts_lock:
            try:
                existing = self._alerts[key]
                if existing == (value):
                    return
            except KeyError:
                pass

            self._alerts[key] = value
            self._delta_alerts.add(key)

    def update_statistic(self, resource, stat, value):
        pass

    def _register_resource(self, resource):
        """Register a newly created resource:
        * Assign it a local ID
        * Add it to the local indices
        * Mark it for inclusion in the next update to global state"""
        assert(isinstance(resource, StorageResource))
        assert(self._handle)
        assert(not resource._handle)

        resource.validate()
        resource._handle = self.generate_handle()
        self._index.add(resource)
        self._delta_new_resources.append(resource._handle)




