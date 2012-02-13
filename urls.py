from django.conf.urls.defaults import patterns, include

from django.contrib import admin
admin.autodiscover()

from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from tastypie.api import Api
api = Api(api_name = 'api')

import chroma_api.alert
import chroma_api.event
import chroma_api.log
import chroma_api.job
import chroma_api.command
import chroma_api.help

import chroma_api.session
import chroma_api.user
import chroma_api.group

import chroma_api.volume
import chroma_api.volume_node
import chroma_api.storage_resource
import chroma_api.storage_resource_class

import chroma_api.host
import chroma_api.filesystem
import chroma_api.target
api.register(chroma_api.host.HostResource())
api.register(chroma_api.host.HostTestResource())
api.register(chroma_api.filesystem.FilesystemResource())
api.register(chroma_api.target.TargetResource())
api.register(chroma_api.volume.VolumeResource())
api.register(chroma_api.volume_node.VolumeNodeResource())
api.register(chroma_api.session.SessionResource())
api.register(chroma_api.user.UserResource())
api.register(chroma_api.group.GroupResource())
api.register(chroma_api.alert.AlertResource())
api.register(chroma_api.event.EventResource())
api.register(chroma_api.job.JobResource())
api.register(chroma_api.log.LogResource())
api.register(chroma_api.command.CommandResource())
api.register(chroma_api.help.HelpResource())

urlpatterns = patterns('',
    (r'^djcelery/', include('djcelery.urls')),
    (r'^admin/', include(admin.site.urls)),

    (r'^api/', include('chroma_api.urls')),
    (r'^ui/', include('chroma_ui.urls')),
    (r'^', include(api.urls)),
)

urlpatterns += staticfiles_urlpatterns()
