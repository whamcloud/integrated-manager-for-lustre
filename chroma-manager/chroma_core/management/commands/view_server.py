#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2016 Intel Corporation All Rights Reserved.
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


import os
import settings
import json

from django.core.management.commands.runserver import Command as BaseCommand


class Command(BaseCommand):
    """
    Setup view-server
    """
    help = """Generates a conf.json file and starts the view-server."""

    def handle(self, *args, **kwargs):
        """
        Generate config a file for the view-server, and send the view-server command to stdout.

        The reason for sending the command to stdout instead of just running
        it is so that supervisord can directly manage the resulting
        process (otherwise we would have to handle passing signals through).
        """
        from chroma_core.lib.util import site_dir

        SITE_ROOT = site_dir()
        VIEW_SERVER_DIR = os.path.join(SITE_ROOT, 'ui-modules', 'node_modules', 'intel-view-server')
        CONF = os.path.join(VIEW_SERVER_DIR, "conf.json")

        conf = {
            "ALLOW_ANONYMOUS_READ": settings.ALLOW_ANONYMOUS_READ,
            "BUILD": settings.BUILD,
            "IS_RELEASE": settings.IS_RELEASE,
            "LOG_PATH": settings.LOG_PATH,
            "SERVER_HTTP_URL": settings.SERVER_HTTP_URL,
            "SITE_ROOT": settings.SITE_ROOT,
            "STATIC_URL": settings.STATIC_URL,
            "VIEW_SERVER_PORT": settings.VIEW_SERVER_PORT,
            "VERSION": settings.VERSION
        }

        json.dump(conf, open(CONF, 'w'), indent=2)

        cmdline = ["node", VIEW_SERVER_DIR + '/server.js']
        print " ".join(cmdline)
