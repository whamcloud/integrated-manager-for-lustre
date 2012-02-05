#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from hydraapi.requesthandler import RequestHandler

from chroma_core.models import StorageResourceClass, StorageResourceRecord
from chroma_core.lib.storage_plugin.manager import storage_plugin_manager


class StorageResourceClassHandler(RequestHandler):
    def get(self, request, module_name = None, class_name = None, creatable = None):
        if module_name and class_name:
            # Return a specific class
            resource_class = StorageResourceClass.objects.get(storage_plugin__module_name = module_name, class_name = class_name)
            return resource_class.to_dict()
        else:
            # Return a list of classes, optionally filtered on 'creatable'
            if creatable:
                resource_classes = storage_plugin_manager.get_resource_classes(scannable_only = True)
                if len(resource_classes):
                    default = resource_classes[0].to_dict()
                else:
                    default = None
            else:
                resource_classes = storage_plugin_manager.get_resource_classes()

                # Pick the first resource with no parents, and use its class
                try:
                    default = StorageResourceRecord.objects.filter(parents = None).latest('pk').resource_class.to_dict()
                except StorageResourceRecord.DoesNotExist:
                    try:
                        default = StorageResourceRecord.objects.all()[0].resource_class.to_dict()
                    except IndexError:
                        try:
                            default = StorageResourceClass.objects.all()[0].to_dict()
                        except IndexError:
                            default = None

            return {
                    'resource_classes': [resource_class.to_dict() for resource_class in resource_classes],
                    'default_hint': default
                    }
