## Copyright 2011 Whamcloud, Inc.
## Authors: Michael MacDonald <mjmac@whamcloud.com>

from r3d.models import Database, Datasource, Archive, CdpPrep, CDP
from django.contrib import admin

admin.site.register(Database)
admin.site.register(Datasource)
admin.site.register(Archive)
admin.site.register(CdpPrep)
admin.site.register(CDP)
