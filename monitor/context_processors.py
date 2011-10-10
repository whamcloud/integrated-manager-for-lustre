
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

def app_data(request):
    from settings import VERSION
    return {'APP_VERSION': VERSION}

def menu_items(request):
    items = []
    from django.core.urlresolvers import reverse
    items.append({"url": reverse('monitor.views.dashboard'), "caption": "Dashboard"})
    items.append({"url": reverse('monitor.views.log_viewer'), "caption": "Log Viewer"})
    items.append({"url": reverse('monitor.views.events'), "caption": "Events"})
    items.append({"url": reverse('monitor.views.alerts'), "caption": "Alerts"})

    try:
        import configure
        items.append({"url": reverse('configure.views.states'), "caption": "Filesystem setup"})
        items.append({"url": reverse('configure.views.storage_table'), "caption": "Storage setup"})
    except ImportError:
        pass

    return {'menu_items': items}
