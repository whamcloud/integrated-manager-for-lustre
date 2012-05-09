#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from r3d.models import Database, Datasource, Archive, ArchiveRow
from django.contrib import admin

admin.site.register(Database)
admin.site.register(Datasource)
admin.site.register(Archive)
admin.site.register(ArchiveRow)
