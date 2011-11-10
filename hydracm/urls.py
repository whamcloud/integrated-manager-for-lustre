
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.conf.urls.defaults import *
from views import (hydracm,
                   hydracmfstab,
                   hydracmmgttab,
                   hydracmvolumetab,
                   hydracmservertab,
                   hydracmnewfstab,
                   hydracmeditfs,
                   storage_tab)

urlpatterns = patterns('',
    (r'^$', hydracm),
    (r'^config/.*$', hydracm),
    (r'^filesystems_tab/', hydracmfstab),
    (r'^mgts_tab/', hydracmmgttab),
    (r'^volumes_tab/', hydracmvolumetab),
    (r'^servers_tab/', hydracmservertab), 
    (r'^storage_tab/', storage_tab),
    (r'^filesystems_new/', hydracmnewfstab),
    (r'^filesystems_edit/', hydracmeditfs)
)
