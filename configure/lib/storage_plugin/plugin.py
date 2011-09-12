
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

import json
import pickle
import settings
from collections_24 import defaultdict

from configure.models import VendorResourceRecord
from configure.lib.storage_plugin.resource import VendorResource, LocalId, GlobalId
from configure.lib.storage_plugin.log import vendor_plugin_log

class VendorPlugin(object):
    def __init__(self):
        from configure.lib.storage_plugin import vendor_plugin_manager
        self._handle = vendor_plugin_manager.register_plugin(self)
        # TODO: give each one its own log, or at least a prefix
        self.log = vendor_plugin_log

    def initial_scan(self):
        """To be implemented by subclasses.  Identify all resources
           present at this time and call register_resource on them.
           
           Any plugin which throws an exception from here is assumed
           to be broken - this will not be retried.  If one of your
           controllers is not contactable, you must handle that and 
           when it comes back up let us know during an update call."""
        raise NotImplementedError

    def get_root_resources(self):
        """Return any existing resources for this plugin which
           have no parents.  e.g. depending on the plugin this
           might be chassis, hosts.  Usually something that 
           holds an IP address for this plugin to reach out to.
           Plugins may call this during their initial_scan 
           implementation.

           This information is not simply included in the arguments
           to initial_scan, because some plugins may either use 
           their own autodiscovery mechanism or run locally on 
           a controller and therefore need no hints from us."""
        from configure.lib.storage_plugin import vendor_plugin_manager 
        records = VendorResourceRecord.objects.\
               filter(vendor_plugin = self.__class__.__module__).\
               filter(parents = None)
        #from django.db.models import Count,F
        #records = VendorResourceRecord.objects.\
        #       filter(vendor_plugin = self.__class__.__module__).\
        #       annotate(Count('parents')).\
        #       filter(F('parents__count') = 0)

        resources = []
        for vrr in records:
            klass = vendor_plugin_manager.get_plugin_resource_class(vrr.vendor_plugin, vrr.vendor_class_str)
            assert(issubclass(klass, VendorResource))
            # Skip populating VendorResource._parents
            vendor_dict = json.loads(vrr.vendor_dict_str)
            resource = klass(**vendor_dict)
            resource._handle = vrr.id
            resources.append(resource)

        return resources

    def register_resource(self, resource):
        """Register a resource:
           * Validate its attributes
           * Create a VendorResourceRecord if it doesn't already
             exist.
           * Update VendorResourceRecord.vendor_dict from resource._vendor_dict
           * Populate its _handle attribute with a reference
             to a VendorResourceRecord.
             
           You may only call this once per plugin instance on 
           a particular resource."""
        assert(isinstance(resource, VendorResource))
        assert(self._handle)
        assert(not resource._handle)

        resource.validate()

        id_string = resource.id_str()

        if isinstance(resource.identifier, GlobalId):
            id_scope = None
        elif isinstance(resource.identifier, LocalId):
            # TODO: support ancestors rather than just parents
            scope_parent = None
            for p in resource._parents:
                if isinstance(p, resource.identifier.parent_klass):
                    scope_parent = p
            if not scope_parent:
                raise RuntimeError("Resource %s scoped to resource of type %s, but has no parent of that type!  Its parents are: %s" % (resource, resource.identifier.parent_klass, resource._parents))
            if not scope_parent._handle:
                raise RuntimeError("Resource %s's scope parent %s has not been registered yet (parents must be registered before children)" % (resource, scope_parent))

            id_scope = VendorResourceRecord.objects.get(pk=scope_parent._handle)

        record, created = VendorResourceRecord.objects.get_or_create(
                vendor_plugin = resource.__class__.__module__,
                vendor_class_str = resource.__class__.__name__,
                vendor_id_str = id_string,
                vendor_id_scope = id_scope)

        record.vendor_dict_str = json.dumps(resource._vendor_dict)
        record.save()

        resource._handle = record.pk
        if created:
            vendor_plugin_log.info("Created VendorResourceRecord for %s id=%s" % (resource.__class__.__name__, id_string))
        else:
            vendor_plugin_log.debug("Looked up VendorResourceRecord %s for %s id=%s" % (record.id, resource.__class__.__name__, id_string))

        for parent in resource._parents:
            if not parent._handle:
                raise RuntimeError("Parent resources must be registered before their children")
            parent_record = VendorResourceRecord.objects.get(pk = parent._handle)
            record.parents.add(parent_record)

    def deregister_resource(self, resource):
        if not resource._handle:
            raise RuntimeError("Cannot deregister resource which has not been registered")

        # TODO: what happens when there are related objects?
        VendorResourceRecord.objects.get(pk = resource._handle).delete()



