# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

from collections import defaultdict
import json
import logging

from django.db import models
from django.db.models import Q, CASCADE

from chroma_core.models import AlertEvent
from chroma_core.models import AlertStateBase
from chroma_core.models import Volume
from chroma_core.models import ManagedTargetMount
from chroma_core.lib.storage_plugin.log import storage_plugin_log as log
from chroma_core.models.sparse_model import VariantDescriptor


# Our limit on the length of python names where we put
# them in CharFields -- python doesn't impose a limit, so this
# is pretty arbitrary
MAX_NAME_LENGTH = 128


class StoragePluginRecord(models.Model):
    """Reference to a module defining a BaseStoragePlugin subclass"""

    module_name = models.CharField(max_length=MAX_NAME_LENGTH)
    internal = models.BooleanField(default=False)

    class Meta:
        unique_together = ("module_name",)
        app_label = "chroma_core"
        ordering = ["id"]
