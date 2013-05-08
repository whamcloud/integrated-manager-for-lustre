#
# INTEL CONFIDENTIAL
#
# Copyright 2013 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


from django.core.management.base import BaseCommand, CommandError
import os
import sys

import settings


class Command(BaseCommand):
    help = """Perform some basic checks on a storage plugin module."""

    def execute(self, *args, **kwargs):
        filename = args[0]
        if not os.path.exists(filename):
            raise CommandError('File not found %s' % filename)
        filename = os.path.abspath(filename)

        parts = filename.strip(os.path.sep).split(os.path.sep)
        module_dir = os.path.sep + os.path.join(*parts[0:-1])
        if os.path.isdir(filename):
            # Dir name is module name
            module_name = parts[-1]
        else:
            # Strip off .py
            module_name = parts[-1][0:-3]

        if not module_dir in sys.path:
            sys.path.append(module_dir)

        settings.INSTALLED_STORAGE_PLUGINS = ['linux']
        from chroma_core.lib.storage_plugin.manager import StoragePluginManager
        manager = StoragePluginManager()

        print "Validating plugin '%s'..." % module_name
        errors = manager.validate_plugin(module_name)
        if errors:
            print "Validation errors:"
            for e in errors:
                print "  %s" % e
        else:
            print "OK"

        # Returning does nothing when run normally, but is useful for testing
        return errors
