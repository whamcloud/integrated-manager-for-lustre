#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from chroma_core.lib.storage_plugin.base_resource import BaseGlobalId, BaseAutoId, BaseScopedId


class GlobalId(BaseGlobalId):
    """An Id which is globally unique"""
    pass


class AutoId(BaseAutoId):
    """An ID generated on resource creation by Chroma"""
    pass


class ScopedId(BaseScopedId):
    """An Id which is unique within a scannable resource"""
    pass
