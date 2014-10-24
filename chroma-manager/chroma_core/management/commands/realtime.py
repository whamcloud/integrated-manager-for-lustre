#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2014 Intel Corporation All Rights Reserved.
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

from optparse import make_option
import logging

from django.core.management.commands.runserver import Command as BaseCommand


class Command(BaseCommand):
    """
    Setup node realtime module
    """
    help = """Generates a conf.json file and starts the realtime module."""
    args = 'type'

    option_list = BaseCommand.option_list + (
        make_option('--type',
                    action='store',
                    default='prod',
                    help='The type of environment the realtime module is starting in.'),
    )

    def handle(self, *args, **kwargs):
        """
        Generate config files for the realtime module, and send the node realtime command to stdout.

        The reason for sending the command to stdout instead of just running
        it is so that supervisord can directly manage the resulting node
        process (otherwise we would have to handle passing signals through).
        """
        from chroma_core.lib.util import site_dir

        SITE_ROOT = site_dir()
        REALTIME_DIR = os.path.join(SITE_ROOT, "realtime")
        CONF = os.path.join(REALTIME_DIR, "conf.json")

        if settings.LOG_LEVEL == logging.DEBUG or settings.DEBUG:
            mode = 'DEV'
        else:
            mode = 'PROD'

        conf = {
            "PRIMUS_PORT": settings.REALTIME_PORT,
            "SERVER_HTTP_URL": settings.SERVER_HTTP_URL,
            "MODE": mode,
            "SOURCE_MAP_DIR": os.path.join(SITE_ROOT, "chroma_ui_new", "static", "chroma_ui", "built*.map")
        }

        json.dump(conf, open(CONF, 'w'), indent=2)

        cmdline = ["node", REALTIME_DIR]
        print " ".join(cmdline)
