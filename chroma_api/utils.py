
from chroma_api.requesthandler import APIResponse


def paginate_result(page_id, page_size, result, format_fn, sEcho = None):
    """Paginate a django QuerySet into the form expected by jquery.datatables"""
    if page_id:
        offset = int(page_id)
    else:
        offset = 0
    # iTotalRecords is the number of records before filtering (where here filtering
    # means datatables filtering, not the filtering we're doing from our other args)
    iTotalRecords = result.count()
    # This is equal because we are not doing any datatables filtering here yet.
    iTotalDisplayRecords = iTotalRecords

    if page_size:
        result = result[offset:offset + page_size]

    # iTotalDisplayRecords is simply the number of records we will return
    # in this call (i.e. after all filtering and pagination)
    paginated_result = {}
    paginated_result['iTotalRecords'] = iTotalRecords
    paginated_result['iTotalDisplayRecords'] = iTotalDisplayRecords
    paginated_result['aaData'] = [format_fn(r) for r in result]
    if sEcho:
        paginated_result['sEcho'] = int(sEcho)

    # Use cache=False to get some anti-caching headers set on the
    # HTTP response: necessary because /event/?iDisplayStart=0 is
    # actually something that changes due to backwards-time-sorting.
    return APIResponse(paginated_result, 200, cache = False)

from django.contrib.contenttypes.models import ContentType
from configure.lib.state_manager import StateManager
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
            # FIXME: this should be a GET to something like /foo/transitions/from/to/
            #        to get information about that transition.
            from configure.lib.state_manager import StateManager
            report = StateManager().get_transition_consequences(bundle.obj, new_state)
            raise custom_response(self, request, http.HttpResponse, report)
        else:
            from configure.models import Command
            command = Command.set_state(bundle.obj, new_state)
            raise custom_response(self, request, http.HttpAccepted, command.to_dict())
