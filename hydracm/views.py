
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

# Create your views here.
from django.core.management import setup_environ
import settings
setup_environ(settings)

from django.shortcuts import render_to_response
from django.template import RequestContext


def hydracm(request):
    return render_to_response("configuration_home.html",
            RequestContext(request, {}))

def hydracmfstab(request):
    return render_to_response("lustre_fs_configuration.html",
            RequestContext(request, {}))

def hydracmmgttab(request):
    return render_to_response("new_mgt.html",
            RequestContext(request, {}))

def hydracmvolumetab(request):
    return render_to_response("volume_configuration.html",
            RequestContext(request, {}))

def hydracmservertab(request):
    return render_to_response("server_configuration.html",
            RequestContext(request, {}))

def storage_tab(request):
    return render_to_response("storage_configuration.html",
            RequestContext(request, {}))

def hydracmnewfstab(request):
    return render_to_response("create_lustre_fs.html",
            RequestContext(request, {}))

def hydracmeditfs(request):
    fs_name=request.GET.get("fs_name")
    fs_id=request.GET.get("fs_id")
    return render_to_response("edit_fs.html",
            RequestContext(request, {"fs_name":fs_name,"fs_id":fs_id}))
