from django.conf.urls.defaults import *

from django.contrib import admin
admin.autodiscover()

from django.contrib.staticfiles.urls import staticfiles_urlpatterns

urlpatterns = patterns('',
    # Example:
    (r'^monitor/', include('monitor.urls')),

    (r'^djcelery/', include('djcelery.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    (r'^admin/', include(admin.site.urls)),
)

urlpatterns += staticfiles_urlpatterns()
