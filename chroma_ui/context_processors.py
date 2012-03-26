
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

import settings


def app_version(request):
    return {'app_version': settings.VERSION}
