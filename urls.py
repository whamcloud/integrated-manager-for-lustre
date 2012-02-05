from django.conf.urls.defaults import patterns, include

from django.contrib import admin
admin.autodiscover()

from django.contrib.staticfiles.urls import staticfiles_urlpatterns

urlpatterns = patterns('',
    (r'^djcelery/', include('djcelery.urls')),
    (r'^api/', include('chroma_api.urls')),
    (r'^dashboard/', include('hydradashboard.urls')),
    (r'^hydracm/', include('chroma_ui.urls')),
    # Uncomment the admin/doc line below to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    (r'^admin/', include(admin.site.urls)),
)

urlpatterns += staticfiles_urlpatterns()
