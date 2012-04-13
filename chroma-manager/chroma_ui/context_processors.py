#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import settings


def app_version(request):
    return {'app_version': settings.VERSION}
