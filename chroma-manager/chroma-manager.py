#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2015 Intel Corporation All Rights Reserved.
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
import sys

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
sys.path.insert(0, SITE_ROOT)

os.environ['CELERY_LOADER'] = 'django'

import multiprocessing
workers = multiprocessing.cpu_count() * 2 + 1

worker_class = 'gevent'

import settings

bind = "127.0.0.1:%s" % settings.HTTP_API_PORT

errorlog = os.path.join(settings.LOG_PATH, 'gunicorn-error.log')
accesslog = os.path.join(settings.LOG_PATH, 'gunicorn-access.log')

timeout = settings.LONG_POLL_TIMEOUT_SECONDS + 10

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()


def on_starting(server):
    from chroma_core.services.log import log_set_filename
    log_set_filename('http.log')
