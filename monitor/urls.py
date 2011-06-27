from django.conf.urls.defaults import *

from monitor.views import *

urlpatterns = patterns('',
    (r'^$', dashboard),
    (r'^dashboard_inner/$', dashboard_inner),
    (r'^statistics/$', statistics),
    (r'^statistics_inner/$', statistics_inner),
    (r'^statistics/statistics_inner/$', statistics_inner), # FIXME: why is this needed?
    (r'^graphs/((target|server|router)/[\w\.\-]+)$', graph_loader),
    (r'^dyngraphs/((target|server|router)/[\w\.\-]+)$', dyn_graph_loader),
)
