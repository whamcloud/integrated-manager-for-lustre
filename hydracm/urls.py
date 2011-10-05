
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.conf.urls.defaults import *
from views import (hydracm,
                   hydracmfstab,
                   hydracmmgttab,
                   hydracmvolumetab,
                   hydracmservertab,
                   hydracmnewfstab)

urlpatterns = patterns('',
    (r'^$', hydracm),
    (r'^fstab/', hydracmfstab),
    (r'^mgttab/', hydracmmgttab),
    (r'^volumetab/', hydracmvolumetab),
    (r'^servertab/', hydracmservertab), 
    (r'^newfstab/', hydracmnewfstab),
)
