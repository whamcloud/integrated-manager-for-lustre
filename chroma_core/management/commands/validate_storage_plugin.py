# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from django.core.management.base import BaseCommand, CommandError
import os
import sys

import settings


class Command(BaseCommand):
    help = """Perform some basic checks on a storage plugin module."""

    def execute(self, *args, **kwargs):
        filename = args[0]
        if not os.path.exists(filename):
            raise CommandError("File not found %s" % filename)
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

        settings.INSTALLED_STORAGE_PLUGINS = ["linux"]
        from chroma_core.lib.storage_plugin.manager import StoragePluginManager

        manager = StoragePluginManager()

        print("Validating plugin '%s'..." % module_name)
        errors = manager.validate_plugin(module_name)
        if errors:
            print("Validation errors:")
            for e in errors:
                print("  %s" % e)
        else:
            print("OK")

        # Returning does nothing when run normally, but is useful for testing
        return errors
