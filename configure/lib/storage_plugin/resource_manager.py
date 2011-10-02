
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
"""

from configure.lib.storage_plugin.log import storage_plugin_log as log
from configure.lib.storage_plugin.resource import ScannableId, GlobalId
from configure.lib.storage_plugin.manager import storage_plugin_manager

from django.db import transaction

import threading

class PluginSession(object):
    def __init__(self, scannable_id):
        self.local_id_to_global_id = {}
        self.scannable_id = scannable_id

class ResourceManager(object):
    def __init__(self):
        self._sessions = {}
        self._instance_lock = threading.Lock()

    def resource_get_alerts(resource):
        # NB assumes resource is a out-of-plugin instance
        # which has _handle set to a DB PK
        assert(resource._handle != None)
        from configure.models import StorageResourceAlert
        from configure.models import StorageResourceRecord
        resource_alerts = StorageResourceAlert.filter_by_item_id(
                StorageResourceRecord, resource._handle)

        return list(resource_alerts)

    def session_open(self, scannable_id, initial_resources):
        with self._instance_lock:
            if scannable_id in self._sessions:
                log.warning("Clearing out old session for scannable ID %s" % scannable_id)
                del self._sessions[scannable_id]

            session = PluginSession(scannable_id)
            self._sessions[scannable_id] = session
            self._persist_new_resources(session, initial_resources)
            
            # TODO: cull any resources which are in the database with
            # ScannableIds for this scannable

    def session_update_resource(self, scannable_id, local_resource_id, attrs):
        with self._instance_lock:
            session = self._sessions[scannable_id]
            record_pk = session.local_id_to_global_id[local_resource_id]

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
            pass

    def session_notify_alert(self, scannable_id, resource_local_id, active, alert_class, attribute):
        with self._instance_lock:
            session = self._sessions[scannable_id]
            record_pk = session.local_id_to_global_id[local_resource_id]
            from configure.models import StorageResourceRecord
            record = StorageResourceRecord.objects.get(record_pk)
            # TODO transaction
            StorageResourceAlert.notify(record, active, alert_class=alert_class, attribute=attribute)
    
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
                # TODO: fire off an event for this discovery
                log.info("Created SRR %s (class %s id %s scope %s)" % (record.pk,
                    r.__class__.__name__, r.id_str(), scope_id))
            else:
                log.debug("Loaded existing SRR %s (class %s id %s scope %s)" % (record.pk,
                    r.__class__.__name__, r.id_str(), scope_id))
            session.local_id_to_global_id[r._handle] = record.pk
            self._resource_persist_attributes(r, record)
            record_cache[record.pk] = record

        # Do a separate pass for parents so that we will have already
        # built the full local-to-global map
        for r in resources:
            record = record_cache[session.local_id_to_global_id[r._handle]]
            self._resource_persist_parents(r, session, record)

    @transaction.autocommit
    def _resource_persist_attributes(self, resource, record):
        record.update_attributes(resource._storage_dict)

    @transaction.autocommit
    def _resource_persist_parents(self, resource, session, record):
        from configure.models import StorageResourceRecord

        new_parent_pks = [session.local_id_to_global_id[p._handle] for p in resource._parents]
        existing_parents = record.parents.all()

        for ep in existing_parents:
            if not ep.pk in new_parent_pks:
                record.parents.remove(ep)

        existing_parent_handles = [ep.pk for ep in existing_parents]
        for pk in new_parent_pks:
            if not pk in existing_parent_handles:
                record.parents.add(pk)

resource_manager = ResourceManager()
