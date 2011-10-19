
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
    (r'^fstab/', hydracmfstab),
    (r'^mgttab/', hydracmmgttab),
    (r'^volumetab/', hydracmvolumetab),
    (r'^servertab/', hydracmservertab), 
    (r'^newfstab/', hydracmnewfstab),
    (r'^editfs/', hydracmeditfs),
    (r'^storage_tab/', storage_tab)
)
