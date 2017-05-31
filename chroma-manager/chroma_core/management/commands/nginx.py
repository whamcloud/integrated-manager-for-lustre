# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import os
from functools import partial

from django.template import Template, Context
from django.core.management.commands.runserver import Command as BaseCommand

import settings


class Command(BaseCommand):
    """
    Set up a nginx config to work in development
    """

    @property
    def _nginx_path(self):
        paths = ["/usr/sbin/nginx", "/usr/local/bin/nginx"]
        for path in paths:
            if os.path.exists(path):
                return path

        raise RuntimeError("Nginx binary not found (tried %s)" % paths)

    def handle(self, *args, **kwargs):
        """
        Generate config files for running nginx, and send the nginx command
        line to stdout.

        The reason for sending the command line to stdout instead of just running
        it is so that supervisord can directly manage the resulting nginx
        process (otherwise we would have to handle passing signals through).
        """
        from chroma_core.lib.util import site_dir

        # This command is only for development
        assert settings.DEBUG

        SITE_ROOT = site_dir()
        join_site_root = partial(os.path.join, SITE_ROOT)

        DEV_NGINX_DIR = join_site_root("dev_nginx")
        join_nginx_dir = partial(join_site_root, DEV_NGINX_DIR)

        NGINX_CONF_TEMPLATE = join_site_root("nginx.conf.template")
        NGINX_CONF = join_nginx_dir("nginx.conf")

        CHROMA_MANAGER_CONF_TEMPLATE = join_site_root("chroma-manager.conf.template")
        CHROMA_MANAGER_CONF = join_nginx_dir("chroma-manager.conf")

        if not os.path.exists(DEV_NGINX_DIR):
            os.makedirs(DEV_NGINX_DIR)

        def write_conf(template_path, conf_path):
            conf_text = Template(open(template_path).read()).render(Context({
                'var': DEV_NGINX_DIR,
                'log': SITE_ROOT,
                'SSL_PATH': settings.SSL_PATH,
                'APP_PATH': settings.APP_PATH,
                'REPO_PATH': settings.DEV_REPO_PATH,
                'HTTP_FRONTEND_PORT': settings.HTTP_FRONTEND_PORT,
                'HTTPS_FRONTEND_PORT': settings.HTTPS_FRONTEND_PORT,
                'HTTP_AGENT_PORT': settings.HTTP_AGENT_PORT,
                'HTTP_API_PORT': settings.HTTP_API_PORT,
                'REALTIME_PORT': settings.REALTIME_PORT,
                'VIEW_SERVER_PORT': settings.VIEW_SERVER_PORT
            }))
            open(conf_path, 'w').write(conf_text)

        write_conf(NGINX_CONF_TEMPLATE, NGINX_CONF)
        write_conf(CHROMA_MANAGER_CONF_TEMPLATE, CHROMA_MANAGER_CONF)

        print " ".join([self._nginx_path, "-c", NGINX_CONF])
