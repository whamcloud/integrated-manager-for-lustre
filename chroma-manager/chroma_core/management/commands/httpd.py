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


import sys
import os

from distutils.sysconfig import get_python_lib

from django.template import Template, Context
from django.core.management.commands.runserver import Command as BaseCommand

import settings


class Command(BaseCommand):
    """
    Set up an apache config to work in development
    mode as an unprivileged user
    """

    @property
    def _wsgi_path(self):
        WSGI_LOCATIONS = [
            '/usr/lib64/httpd/modules/mod_wsgi.so',  # CentOS 6 location
            '/usr/libexec/apache2/mod_wsgi.so',                    # OS X + macports location
            '/usr/local/Cellar/mod_wsgi/3.4/libexec/mod_wsgi.so',  # OS X + homebrew locations
            '/usr/local/Cellar/mod_wsgi/3.3/libexec/mod_wsgi.so',
        ]
        for path in WSGI_LOCATIONS:
            if os.path.exists(path):
                return path

        raise RuntimeError("WSGI module not found (yum install mod_wsgi, or "
                           "https://github.com/Homebrew/homebrew-apache).  Tried locations: %s" % WSGI_LOCATIONS)

    @property
    def _module_path(self):
        PATHS = ["/usr/libexec/apache2/", "/usr/lib64/httpd/modules/"]
        for path in PATHS:
            if os.path.exists(path):
                return path

        raise RuntimeError("Apache module path not found (tried %s)" % PATHS)

    def handle(self, *args, **kwargs):
        """
        Generate config files for running apache, and send the httpd command
        line to stdout.

        The reason for sending the command line to stdout instead of just running
        it is so that supervisord can directly manage the resulting apache
        process (otherwise we would have to handle passing signals through).
        """
        from chroma_core.lib.util import site_dir

        # This command is only for development
        assert settings.DEBUG

        SITE_ROOT = site_dir()
        DEV_HTTPD_CONF_TEMPLATE = os.path.join(SITE_ROOT, "chroma-manager.conf.template")
        HTTPD_BIN = "/usr/sbin/httpd"

        DEV_HTTPD_DIR = os.path.join(SITE_ROOT, "dev_httpd")
        if not os.path.exists(DEV_HTTPD_DIR):
            os.makedirs(DEV_HTTPD_DIR)
        DEV_HTTPD_CONF = os.path.join(DEV_HTTPD_DIR, "httpd.conf")
        conf_text = Template(open(DEV_HTTPD_CONF_TEMPLATE).read()).render(Context({
            'var': DEV_HTTPD_DIR,
            'log': SITE_ROOT,
            'SSL_PATH': settings.SSL_PATH,
            'APP_PATH': settings.APP_PATH,
            'wsgi_path': self._wsgi_path,
            'module_path': self._module_path,
            'REPO_PATH': settings.DEV_REPO_PATH,
            'HTTP_FRONTEND_PORT': settings.HTTP_FRONTEND_PORT,
            'HTTPS_FRONTEND_PORT': settings.HTTPS_FRONTEND_PORT,
            'HTTP_AGENT_PORT': settings.HTTP_AGENT_PORT,
            'HTTP_API_PORT': settings.HTTP_API_PORT,
            'REALTIME_PORT': settings.REALTIME_PORT,
            'WSGI_PYTHON_PATH': get_python_lib()
        }))
        open(DEV_HTTPD_CONF, 'w').write(conf_text)

        # Value used for conditional regions of config
        CHROMA_DEV_FLAG = "ChromaDev"

        cmdline = [HTTPD_BIN, "-D", CHROMA_DEV_FLAG, "-D", "NO_DETACH", "-D", "FOREGROUND", "-f", DEV_HTTPD_CONF]
        sys.stderr.write("Run this:\n")
        print " ".join(cmdline)
