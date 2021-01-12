# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import tarfile
from chroma_core.lib.util import site_dir
import os
import sys
import glob
import json

from django.core.management import BaseCommand
import settings


class Command(BaseCommand):
    def handle(self, *args, **options):
        from chroma_core.lib import service_config

        sc = service_config.ServiceConfig()
        sc._setup_rabbitmq_credentials()
        sc._setup_crypto()
        sc._syncdb()
        sc.scan_repos()

        profile_path = os.path.join(site_dir(), "../chroma-bundles/base_managed_RH7.profile")

        for profile_path in glob.glob(os.path.join(os.path.dirname(profile_path), "*.profile")):
            with open(profile_path) as profile_file:
                service_config.register_profile(profile_file)

        print(
            """Great success:
 * run `systemctl start emf-manager.target`
 * open %s"""
            % settings.SERVER_HTTP_URL
        )
