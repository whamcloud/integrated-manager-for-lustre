# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


"""This module defines a simple logger which is used by storage_plugin.* and
provided for use by BaseStoragePlugin subclasses"""


from chroma_core.services import log_register

storage_plugin_log = log_register("storage_plugin")
