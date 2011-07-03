from django.conf.urls.defaults import *

from monitor.views import *

urlpatterns = patterns('',
    (r'^$', dashboard),
    (r'^dashboard_inner/$', dashboard_inner),
    (r'^host/$', host),
    (r'^statistics/$', statistics),
    (r'^graphs/((target|server|router)/[\w\.\-]+)$', graph_loader),
    (r'^dyngraphs/((\w+)/[\w\.\-]+),(\w+)(:\w+)?$', dyn_graph_loader),
    (r'^log_viewer/$', log_viewer),
    (r'^events/$', events),
)
