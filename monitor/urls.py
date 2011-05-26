from django.conf.urls.defaults import *

from monitor.views import *

urlpatterns = patterns('',
    (r'^$', dashboard),
)
