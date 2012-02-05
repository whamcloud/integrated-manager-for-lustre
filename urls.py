from django.conf.urls.defaults import patterns, include

from django.contrib import admin
admin.autodiscover()

from django.contrib.staticfiles.urls import staticfiles_urlpatterns

urlpatterns = patterns('',
    (r'^djcelery/', include('djcelery.urls')),
    (r'^admin/', include(admin.site.urls)),

    (r'^api/', include('chroma_api.urls')),
    (r'^ui/', include('chroma_ui.urls')),
)

urlpatterns += staticfiles_urlpatterns()
