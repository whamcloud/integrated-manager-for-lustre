# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from chroma_core.lib.storage_plugin.api import attributes

from tastypie import fields
from chroma_api.authentication import AnonymousAuthentication, PatchedDjangoAuthorization

from chroma_api.chroma_model_resource import ChromaModelResource


def filter_class_ids():
    """Wrapper to avoid importing storage_plugin_manager at module scope (it
    requires DB to construct itself) so that this module can be imported
    for e.g. building docs without a database.

    Return a list of storage resource class IDs which are valid for display (i.e.
    those for which we have a plugin available in this process)
    """
    from django.db.utils import DatabaseError, OperationalError

    try:
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager

        return storage_plugin_manager.resource_class_id_to_class.keys()
    except (OperationalError, DatabaseError):
        # OperationalError if the DB server can't be contacted
        # DatabaseError if the DB exists but isn't populated
        return []
