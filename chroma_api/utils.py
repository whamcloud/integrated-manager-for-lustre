
from django.contrib.contenttypes.models import ContentType
from chroma_core.lib.state_manager import StateManager
import chroma_core.lib.conf_param
from tastypie.resources import ModelResource
from tastypie import fields
from tastypie import http


def custom_response(resource, request, response_klass, response_data):
    from tastypie.exceptions import ImmediateHttpResponse
    from tastypie.utils.mime import build_content_type

    desired_format = resource.determine_format(request)
    response = response_klass(content = resource.serialize(request, response_data, desired_format),
            content_type = build_content_type(desired_format))
    return ImmediateHttpResponse(response = response)


class StatefulModelResource(ModelResource):
    content_type_id = fields.IntegerField()
    available_transitions = fields.ListField()
    label = fields.CharField()

    def dehydrate_available_transitions(self, bundle):
        return StateManager.available_transitions(bundle.obj)

    def dehydrate_content_type_id(self, bundle):
        return ContentType.objects.get_for_model(bundle.obj.__class__).pk

    def dehydrate_label(self, bundle):
        return bundle.obj.get_label()

    # PUT handler for accepting {'state': 'foo', 'dry_run': <true|false>}
    def obj_update(self, bundle, request, **kwargs):
        bundle.obj = self.cached_obj_get(request = request, **self.remove_api_resource_names(kwargs))
        dry_run = bundle.data.get('dry_run', False)
        new_state = bundle.data['state']

        if dry_run:
            # FIXME: should this be a GET to something like /foo/transitions/from/to/
            #        to get information about that transition?
            report = StateManager().get_transition_consequences(bundle.obj, new_state)
            raise custom_response(self, request, http.HttpResponse, report)
        else:
            from chroma_core.models import Command
            command = Command.set_state(bundle.obj, new_state)
            raise custom_response(self, request, http.HttpAccepted, command.to_dict())


class ConfParamResource(StatefulModelResource):
    conf_params = fields.DictField()

    def dehydrate_conf_params(self, bundle):
        try:
            return chroma_core.lib.conf_param.get_conf_params(bundle.obj)
        except NotImplementedError:
            return None

    # PUT handler for accepting {'conf_params': {}}
    def obj_update(self, bundle, request, **kwargs):
        bundle.obj = self.cached_obj_get(request = request, **self.remove_api_resource_names(kwargs))
        if not 'conf_params' in bundle.data:
            super(ConfParamResource, self).obj_update(bundle, request, **kwargs)

        # TODO: validate all the conf_params before trying to set any of them
        try:
            conf_params = bundle.data['conf_params']
            for k, v in conf_params.items():
                chroma_core.lib.conf_param.set_conf_param(bundle.obj, k, v)
        except KeyError:
            # TODO: pass in whole objects every time so that I can legitimately
            # validate the presence of this field
            pass

        return bundle
