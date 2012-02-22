
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

import settings


def page_load_time(request):
    import time
    return {'page_load_time': time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())}

    # TODO: use isoformat here and use dateutils.parser in the corresponding
    # API functions like jobs_since: only reason for not doing it now is that
    # I don't want to bring in the extra dependency.
    #from datetime import datetime
    #return {'page_load_time': datetime.now().isoformat()}


def app_version(request):
    return {'app_version': settings.VERSION}
