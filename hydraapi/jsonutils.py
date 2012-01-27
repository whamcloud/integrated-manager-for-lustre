#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================
#
# Utils for JSON related operations# Utils for JSON related operations# Utils for JSON related operations
from django.http import HttpResponse
from functools import wraps
from django.core.serializers.json import DateTimeAwareJSONEncoder
import urllib2


def render_to_json(**jsonargs):
    """
    Renders a JSON response with a given returned instance. Assumes json.dumps() can
    handle the result. The default output uses an indent of 4.

    @render_to_json()
    def a_view(request, arg1, argN):
        ...
        return {'x': range(4)}
    @render_to_json(indent=2)
    def a_view2(request):
        ...
        return [1, 2, 3]
    """
    def outer(f):
        @wraps(f)
        def inner_json(wrapped_self, request, *args, **kwargs):
            r = HttpResponse(mimetype='application/json')
            errors = None
            result = None
            try:
                from hydraapi.requesthandler import APIResponse
                result = f(wrapped_self, request, *args, **kwargs)
                if isinstance(result, APIResponse):
                    r.status_code = result.status
                    result = result.content
            except Exception as e:
                if hasattr(e, 'message_dict'):
                    errors = e.message_dict
                else:
                    #failure_exception = FailureException(str(e))
                    #errors = failure_exception.message_dicta
                    errors = str(e)
                r = get_http_response_with_status_code(e)
                r.write(construct_json_response(request=request,
                                                success=False,
                                                errors = errors,
                                                response = None,
                                                ))
                return r

            r.write(construct_json_response(request=request,
                                            success=True,
                                            errors = None,
                                            response = result,
                                            ))
            return r
        return inner_json
    return outer


def construct_json_response(request, success, errors=None, response=None):
    if errors is None:
        errors = []

    if response is None:
        response = []
    response_dict = {}
    response_dict['success'] = success
    response_dict['errors'] = errors
    response_dict['response'] = response
    return DateTimeAwareJSONEncoder().encode(response_dict)


def get_http_response_with_status_code(exception=None):
    from django.http import Http404
    from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
    from django.db import  IntegrityError
    exception_status_code = {urllib2.URLError: 400,
                             PermissionDenied: 401,
                             Http404: 404,
                             ObjectDoesNotExist: 404,
                             IntegrityError: 409}
    res = HttpResponse(mimetype='application/json')
    if exception:
        res.status_code = exception_status_code.get(type(exception), None) or exception_status_code.get(exception.__class__.__base__, None) or 500
    return res
