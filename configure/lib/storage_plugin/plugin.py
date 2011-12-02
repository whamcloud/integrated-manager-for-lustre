
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

import settings

from configure.lib.storage_plugin.resource import StorageResource
from configure.lib.storage_plugin.log import storage_plugin_log

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

        # Why don't we need a scope resource in here?
        # Because if it's a ScannableId then only items for that
        # scannable will be in this ResourceIndex (index is per
        # plugin instance), and if it's a GlobalId then it doesn't
        # have a scope.
        resource_id = (resource.id_tuple(), resource.__class__)
        if resource_id in self._resource_id_to_resource:
            raise RuntimeError("Duplicate resource added to index")
        self._resource_id_to_resource[resource_id] = resource

    def remove(self, resource):
        resource_id = (resource.id_tuple(), resource.__class__)
        if not resource_id in self._resource_id_to_resource:
            raise RuntimeError("Remove non-existent resource")

        del self._local_id_to_resource[resource._handle]
        del self._resource_id_to_resource[resource_id]

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
        """Mandatory.  Identify all resources
           present at this time and call register_resource on them.

           If you return from this function you must have succeeded
           in communicating with the scannable resource.  Any
           resources which were present previously and are absent
           when initial_scan returns are assumed to be
           permanently absent and are deleted.  If for any reason
           you cannot return all resources (for example, communication
           failure with a controller), you must raise an exception."""
        raise NotImplementedError

    def update_scan(self, root_resource):
        """Optional.  Perform any required
           periodic refresh of data and update any resource instances.
           Guaranteed that initial_scan will have been called before this."""
        pass

    def teardown(self):
        """Optional.  Perform any teardown
           required before terminating.  Guaranteed not to be called
           concurrently with initial_scan or update_scan.  Guaranteed
           that initial_scan or update_scan will not be called after this.
           Guaranteed that once initial_scan has been entered this will
           later be called unless the whole process terminates
           prematurely.  This function will be called even if initial_scan
           or update_scan raises an exception."""
        pass

    def generate_handle(self):
        with self._handle_lock:
            self._handle_counter += 1
            handle = self._handle_counter
            return handle

    def __init__(self, scannable_id = None):
        from configure.lib.storage_plugin.manager import storage_plugin_manager
        self._handle = storage_plugin_manager.register_plugin(self)
        self._initialized = False

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
        if self._initialized:
            raise RuntimeError("Tried to initialize %s twice!" % self)
        self._initialized = True

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
            for name, ac in resource._alert_conditions.items():
                alert_list = ac.test(resource)
                for name, attribute, active in alert_list:
                    self.notify_alert(active, resource, name, attribute)

    def do_periodic_update(self, root_resource):
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
        from configure.lib.storage_plugin.resource_manager import resource_manager
        resource_manager.session_close(self._scannable_id)

    def commit_resource_creates(self):
        from configure.lib.storage_plugin.resource_manager import resource_manager
        if len(self._delta_new_resources) > 0:
            resource_manager.session_add_resources(self._scannable_id, self._delta_new_resources)
        self._delta_new_resources = []

    def commit_resource_deletes(self):
        from configure.lib.storage_plugin.resource_manager import resource_manager
        # Resources deleted since last update
        if len(self._delta_delete_resources) > 0:
            resource_manager.session_remove_resources(self._scannable_id, self._delta_delete_resources)
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
            for (resource, attribute, alert_class) in self._delta_alerts:
                active = self._alerts[(resource, attribute, alert_class)]
                resource_manager.session_notify_alert(
                        self._scannable_id, resource._handle,
                        active, alert_class, attribute)
            self._delta_alerts.clear()

    def commit_resource_statistics(self):
        self.log.debug(">> Plugin.commit_resource_statistics %s", self._scannable_id)
        sent_stats = 0
        for resource in self._index.all():
            r_stats = resource.flush_stats()
            if len(r_stats) > 0:
                from configure.lib.storage_plugin.resource_manager import resource_manager
                resource_manager.session_update_stats(self._scannable_id, resource._handle, r_stats)
                sent_stats += len(r_stats)
        self.log.debug("<< Plugin.commit_resource_statistics %s (%s sent)", self._scannable_id, sent_stats)

    def update_or_create(self, klass, parents = [], **attrs):
        """Report a storage resource.  If it already exists then
        it will be updated, otherwise it will be created.  The resulting
        resource instance is returned.

        Note that the 'created' return value indicates whether this
        is the first report of the resource within this plugin session,
        not whether it is the first report of the resource ever (e.g.
        from a different or previous plugin session).

        :returns: (resource, created) -- the storage resource and a boolean
                  indicating whether this was the first report this session.
        """
        with self._resource_lock:
            try:
                existing = self._index.get(klass, **attrs)
                for k, v in attrs.items():
                    setattr(existing, k, v)
                for p in parents:
                    existing.add_parent(p)
                for p in parents:
                    assert p._handle != existing._handle
                return existing, False
            except ResourceNotFound:
                resource = klass(parents = parents, **attrs)
                self._register_resource(resource)
                for p in parents:
                    assert p._handle != resource._handle
                return resource, True

    def remove(self, resource):
        """Note: this does not immediately unregister the resource, rather marks it
        for removal at the next periodic update"""
        with self._resource_lock:
            self._index.remove(resource)
            self._delta_delete_resources.append(resource)
            # TODO: it would be useful if local resource instances had a
            # way to invalidate their handles to detect buggy plugins

    def notify_alert(self, active, resource, alert_name, attribute = None):
        # This will be flushed through to the database by update_scan
        key = (resource, attribute, alert_name)
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
        self._delta_new_resources.append(resource)
