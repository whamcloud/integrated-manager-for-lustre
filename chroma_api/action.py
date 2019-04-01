# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from django.contrib.contenttypes.models import ContentType
from tastypie.authorization import DjangoAuthorization
from tastypie.validation import Validation
from tastypie.resources import Resource
from tastypie import fields

from chroma_api.authentication import AnonymousAuthentication
from chroma_api.validation_utils import validate
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient

ID_TYPE = "composite_id"
ID_TYPES = "{}s".format(ID_TYPE)


class ActionValidation(Validation):
    def is_valid(self, bundle, request=None):

        if ID_TYPES not in request.GET:
            return {ID_TYPES: "param is missing"}

        ids = request.GET.getlist(ID_TYPES)

        if not isinstance(ids, list):
            return {ID_TYPES: "param is not an array"}

        for x in ids:
            xs = x.split(":")

            if len(xs) != 2:
                return {ID_TYPES: "Recieved a {} that is not made of two parts".format(ID_TYPE)}

            (content_type, _) = xs

            try:
                ContentType.objects.get_for_id(content_type)
            except ContentType.DoesNotExist:
                return {ID_TYPES: "Got a {} that does not exist".format(ID_TYPE)}

        return {}


class Action(object):
    def __init__(
        self,
        composite_id=None,
        args=None,
        class_name=None,
        confirmation=None,
        display_group=None,
        display_order=None,
        long_description=None,
        state=None,
        verb=None,
    ):
        self.composite_id = composite_id
        self.args = args
        self.class_name = class_name
        self.confirmation = confirmation
        self.display_group = display_group
        self.display_order = display_order
        self.long_description = long_description
        self.state = state
        self.verb = verb


class ActionResource(Resource):
    """
    Returns Available actions (transitions + jobs).
    Meant to be polled by the GUI once per 10s on any
    open action dropdowns.
    """

    args = fields.DictField(attribute="args", readonly=True, null=True)
    composite_id = fields.CharField(attribute="composite_id", readonly=True)
    class_name = fields.CharField(attribute="class_name", readonly=True, null=True)
    confirmation = fields.CharField(attribute="confirmation", readonly=True, null=True)
    display_group = fields.IntegerField(attribute="display_group", readonly=True)
    display_order = fields.IntegerField(attribute="display_order", readonly=True)
    long_description = fields.CharField(attribute="long_description", readonly=True)
    state = fields.CharField(attribute="state", readonly=True, null=True)
    verb = fields.CharField(attribute="verb", readonly=True, null=True)

    class Meta:
        allowed_methods = None
        authentication = AnonymousAuthentication()
        authorization = DjangoAuthorization()
        validation = ActionValidation()
        object_class = Action
        resource_name = "action"
        list_allowed_methods = ["get"]

    # Create our array of custom data
    def get_object_list(self, request):
        raw_ids = request.GET.getlist(ID_TYPES)
        ids = map(lambda x: x.split(":"), raw_ids)
        ids = map(lambda x: (int(x[0]), int(x[1])), ids)

        computed_transitions = JobSchedulerClient.available_transitions(ids)
        computed_jobs = JobSchedulerClient.available_jobs(ids)

        actions = []

        #  decorate the transition lists with verbs
        #  and install in the bundle for return
        for y in raw_ids:
            obj_transitions_states_and_verbs = computed_transitions[y]
            obj_jobs = computed_jobs[y]

            available_actions = sorted(
                obj_transitions_states_and_verbs + obj_jobs, key=lambda action: action["display_order"]
            )
            actions += map(lambda x: Action(y, **x), available_actions)

        return actions

    @validate
    def obj_get_list(self, bundle, **kwargs):
        return self.get_object_list(bundle.request)
