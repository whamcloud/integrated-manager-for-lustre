from django.conf.urls.defaults import patterns, include

from django.contrib import admin
admin.autodiscover()

from django.contrib.staticfiles.urls import staticfiles_urlpatterns

urlpatterns = patterns('',
    (r'^djcelery/', include('djcelery.urls')),
    (r'^admin/', include(admin.site.urls)),

    (r'^ui/', include('chroma_ui.urls')),

    (r'^', include('chroma_api.urls')),
)

urlpatterns += staticfiles_urlpatterns()
