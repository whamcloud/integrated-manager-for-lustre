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


from StringIO import StringIO
import tarfile
import os

from django.core.management import BaseCommand
import settings


class Command(BaseCommand):
    def handle(self, *args, **options):
        from chroma_core.lib.service_config import ServiceConfig

        sc = ServiceConfig()
        sc._setup_rabbitmq_credentials()
        sc._setup_crypto()
        sc._syncdb()

        BUNDLE_NAMES = ['lustre', 'chroma-agent', 'e2fsprogs']

        import chroma_core.lib.service_config
        from chroma_core.models import Bundle, ServerProfile

        missing_bundles = False
        for bundle_name in BUNDLE_NAMES:
            path = os.path.join(settings.DEV_REPO_PATH, bundle_name)
            if not os.path.exists(os.path.join(path, 'meta')):
                tarball_path = os.path.join(settings.DEV_REPO_PATH, bundle_name) + "-bundle.tar.gz"
                if os.path.exists(tarball_path):
                    print "Extracting %s" % bundle_name
                    if not os.path.exists(path):
                        os.makedirs(path)
                    archive = tarfile.open(tarball_path, "r:gz")
                    archive.list()
                    archive.extractall(path)
                else:
                    print "Missing bundle %s" % bundle_name
                    missing_bundles = True

            else:
                if not Bundle.objects.filter(location=path).exists():
                    chroma_core.lib.service_config.bundle('register', path)

        if missing_bundles:
            print "Obtain bundles from Jenkins or build them yourself on a linux host, then unpack in %s" % settings.DEV_REPO_PATH
            return

        # FIXME: having to copy-paste this because the production version is embedded in a .sh
        base_profile = """
        {
            "name": "base_managed",
            "bundles": ["lustre", "chroma-agent", "e2fsprogs"],
            "ui_name": "Managed storage server",
            "ui_description": "A storage server suitable for creating new HA-enabled filesystem targets",
            "managed": true
        }
"""
        if not ServerProfile.objects.filter(name = 'base_managed').exists():
            chroma_core.lib.service_config.register_profile(StringIO(base_profile))

        print """Great success:
 * run `./manage.py supervisor`
 * open %s""" % settings.SERVER_HTTP_URL
