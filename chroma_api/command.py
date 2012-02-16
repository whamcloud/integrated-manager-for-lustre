#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from chroma_core.models import Command
from tastypie.resources import ModelResource
from tastypie import fields


class CommandResource(ModelResource):
    """
    Commands are created for asynchronous user actions (202 ACCEPTED responses
    contain command objects).  The command resource can be used to query the details
    and state of these asynchronous operations.

    Typically this is used to poll a command for completion and find out whether it
    succeeded.
    """
    jobs = fields.ToManyField("chroma_api.job.JobResource", 'jobs',
            help_text = "Jobs belonging to this command (not populated until \
                    ``jobs_created`` is true")

    class Meta:
        queryset = Command.objects.all()
        list_allowed_methods = ['get']
        detail_allowed_methods = ['get']
