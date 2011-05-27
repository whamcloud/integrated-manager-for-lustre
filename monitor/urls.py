from django.conf.urls.defaults import *

from monitor.views import *

urlpatterns = patterns('',
    (r'^$', dashboard),
    (r'^dashboard_inner/$', dashboard_inner),
)
