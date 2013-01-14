#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import os

from django.template import Template, Context
from django.core.management.commands.runserver import Command as BaseCommand

import settings


class Command(BaseCommand):
    """
    Run apache, using configuration files modified to work in development
    mode as an unprivileged user
    """
    def handle(self, *args, **kwargs):
        """
        Generate config files for running apache, and send the httpd command
        line to stdout.

        The reason for sending the command line to stdout instead of just running
        it is so that supervisord can directly manage the resulting apache
        process (otherwise we would have to handle passing signals through).
        """
        from chroma_core.lib.util import site_dir

        SITE_ROOT = site_dir()
        # TODO: fill out a template to generate a temporary dev config file
        DEV_HTTPD_CONF_TEMPLATE = os.path.join(SITE_ROOT, "chroma-manager.conf")
        HTTPD_BIN = "/usr/sbin/httpd"

        DEV_HTTPD_DIR = os.path.join(SITE_ROOT, "dev_httpd")
        if not os.path.exists(DEV_HTTPD_DIR):
            os.makedirs(DEV_HTTPD_DIR)
        DEV_HTTPD_CONF = os.path.join(DEV_HTTPD_DIR, "httpd.conf")
        conf_text = Template(open(DEV_HTTPD_CONF_TEMPLATE).read()).render(Context({
            'var': DEV_HTTPD_DIR,
            'log': SITE_ROOT,
            'ssl': SITE_ROOT,
            'app': SITE_ROOT,
            'wsgi_path': '/usr/local/Cellar/mod_wsgi/3.3/libexec/mod_wsgi.so',
            'HTTP_FRONTEND_PORT': settings.HTTP_FRONTEND_PORT,
            'HTTPS_FRONTEND_PORT': settings.HTTPS_FRONTEND_PORT,
            'HTTP_AGENT_PORT': settings.HTTP_AGENT_PORT,
            'HTTP_API_PORT': settings.HTTP_API_PORT,
        }))
        open(DEV_HTTPD_CONF, 'w').write(conf_text)

        cmdline = [HTTPD_BIN, "-D", "NO_DETACH", "-D", "FOREGROUND", "-f", DEV_HTTPD_CONF]
        print " ".join(cmdline)
