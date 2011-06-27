from django.conf.urls.defaults import *

from monitor.views import *

urlpatterns = patterns('',
    (r'^$', dashboard),
    (r'^dashboard_inner/$', dashboard_inner),
    (r'^statistics/$', statistics),
    (r'^graphs/((target|server|router)/[\w\.\-]+)$', graph_loader),
    (r'^dyngraphs/((target|server|router)/[\w\.\-]+),(clients|lock|space|bw|ops|inodes|cpumem)(:\w+)?$', dyn_graph_loader),
    (r'^log_viewer/$', log_viewer),
)
