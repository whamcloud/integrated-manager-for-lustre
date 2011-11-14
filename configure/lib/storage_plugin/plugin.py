
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

import settings

from configure.lib.storage_plugin.resource import StorageResource
from configure.lib.storage_plugin.log import storage_plugin_log
from monitor.lib.util import timeit

import threading

class ResourceNotFound(Exception):
    pass

class ResourceIndex(object):
    def __init__(self, scannable_id):
        # Map (local_id) to resource
        self._local_id_to_resource = {}

        # Map (id_tuple, klass) to resource
        self._resource_id_to_resource = {}

    def add(self, resource):
        self._local_id_to_resource[resource._handle] = resource
        resource.id_tuple()

        # Why don't we need a scope resource in here?
        # Because if it's a ScannableId then only items for that
        # scannable will be in this ResourceIndex (index is per
        # plugin instance), and if it's a GlobalId then it doesn't
        # have a scope.
        resource_id = (resource.id_tuple(), resource.__class__)
        if resource_id in self._resource_id_to_resource:
            raise RuntimeError("Duplicate resource added to index")
        self._resource_id_to_resource[resource_id] = resource

    def get(self, klass, **attrs):
        id_tuple = klass(**attrs).id_tuple()
        try:
            return self._resource_id_to_resource[(id_tuple, klass)]
        except KeyError:
            raise ResourceNotFound()

    def all(self):
        return self._local_id_to_resource.values()

class StoragePlugin(object):
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
           periodic refresh of data and update any resource instances.
           Guaranteed that initial_scan will have been called before this."""
        pass

    def teardown(self):
        """Optionally implemented by subclasses.  Perform any teardown
           required before terminating.  Guaranteed not to be called
           concurrently with initial_scan or update_scan.  Guaranteed
           that initial_scan or update_scan will not be called after this."""
        pass

    def generate_handle(self):
        with self._handle_lock:
            self._handle_counter += 1
            handle = self._handle_counter
            return handle

    def __init__(self, scannable_id = None):
        from configure.lib.storage_plugin.manager import storage_plugin_manager
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

        self.update_period = settings.PLUGIN_DEFAULT_UPDATE_PERIOD

    def do_initial_scan(self, root_resource):
        from configure.lib.storage_plugin.resource_manager import resource_manager 

        root_resource._handle = self.generate_handle()
        root_resource._handle_global = False

        self._index.add(root_resource)

        self.initial_scan(root_resource)

        resource_manager.session_open(
                self._scannable_id,
                root_resource._handle,
                self._index.all(),
                self.update_period)
        self._delta_new_resources = []

        # Creates, deletes, attrs, parents are all handled in session_open
        # the rest we do manually.
        self.commit_resource_statistics()
        self.check_alert_conditions()
        self.commit_alerts()

    def check_alert_conditions(self):
        for resource in self._index.all():
            # Check if any AlertConditions are matched
            for name,ac in resource._alert_conditions.items():
                alert_list = ac.test(resource)
                for name, attribute, active in alert_list:
                    self.notify_alert(active, resource, name, attribute)

    def do_periodic_update(self, root_resource):
        from configure.lib.storage_plugin.resource_manager import resource_manager 
        self.update_scan(root_resource)

        # Resources created since last update
        with self._resource_lock:
            self.commit_resource_creates()
            self.commit_resource_deletes()
            self.commit_resource_updates()
            self.commit_resource_statistics()
            self.check_alert_conditions()
            self.commit_alerts()

    def do_teardown(self):
        self.teardown()

    def commit_resource_creates(self):
        from configure.lib.storage_plugin.resource_manager import resource_manager 
        if len(self._delta_new_resources) > 0:
            resource_manager.session_add_resources(self._scannable_id, self._delta_new_resources)
        self._delta_new_resources = []

    def commit_resource_deletes(self):
        from configure.lib.storage_plugin.resource_manager import resource_manager 
        # Resources deleted since last update
        if len(self._delta_delete_resources) > 0:
            resource_manager.session_add_resources(self._scannable_id, self._delta_delete_resources)
        self._delta_delete_resources = []

    def commit_resource_updates(self):
        from configure.lib.storage_plugin.resource_manager import resource_manager 
        # Resources with changed attributes
        for resource in self._index.all():
            deltas = resource.flush_deltas()
            # If there were changes to attributes
            if len(deltas['attributes']) > 0:
                resource_manager.session_update_resource(
                        self._scannable_id, resource._handle, deltas['attributes']) 

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

    def commit_alerts(self):
        from configure.lib.storage_plugin.resource_manager import resource_manager 
        with self._alerts_lock:
            for (resource,attribute,alert_class) in self._delta_alerts:
                active = self._alerts[(resource,attribute,alert_class)]
                resource_manager.session_notify_alert(
                        self._scannable_id, resource._handle,
                        active, alert_class, attribute)
            self._delta_alerts.clear()

    @timeit(logger = storage_plugin_log)
    def commit_resource_statistics(self):
        self.log.debug(">> Plugin.commit_resource_statistics %s", self._scannable_id)
        sent_stats = 0
        for resource in self._index.all():
            r_stats = resource.flush_stats()
            from configure.lib.storage_plugin.resource_manager import resource_manager 
            resource_manager.session_update_stats(self._scannable_id, resource._handle, r_stats)
            sent_stats += len(r_stats)
        self.log.debug("<< Plugin.commit_resource_statistics %s (%s sent)", self._scannable_id, sent_stats)

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
        resource._handle_global = False

        resource._plugin = self
        self._index.add(resource)
        self._delta_new_resources.append(resource._handle)

