# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import os
import sys

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
sys.path.insert(0, SITE_ROOT)

import multiprocessing
workers = multiprocessing.cpu_count() * 2 + 1

worker_class = 'gevent'

import settings

bind = "127.0.0.1:%s" % settings.HTTP_API_PORT

pidfile = settings.GUNICORN_PID_PATH

errorlog = os.path.join(settings.LOG_PATH, 'gunicorn-error.log')
accesslog = os.path.join(settings.LOG_PATH, 'gunicorn-access.log')

timeout = settings.LONG_POLL_TIMEOUT_SECONDS + 10

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()


def on_starting(server):
    from chroma_core.services.log import log_set_filename
    log_set_filename('http.log')
