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
    Run the wrapped function, and:
     * If it throws an exception, generate an HTTP response with appropriate error status code
     * If it returns an APIResponse, use the status_code and content to populate an HTTP response
     * Else, return an HTTP response with the return value JSON encoded and a status of 200
    """
    def outer(f):
        @wraps(f)
        def inner_json(wrapped_self, request, *args, **kwargs):
            r = HttpResponse(mimetype='application/json')
            errors = None
            try:
                from hydraapi.requesthandler import APIResponse
                result = f(wrapped_self, request, *args, **kwargs)
                if isinstance(result, APIResponse):
                    r.status_code = result.status
                    content = result.content
                else:
                    content = result
            except Exception as e:
                r = exception_to_response(e)
                try:
                    errors = e.message_dict
                except AttributeError:
                    errors = [str(e)]

                r.write(DateTimeAwareJSONEncoder().encode({'errors': errors}))
                return r

            r.write(DateTimeAwareJSONEncoder().encode(content))

            return r
        return inner_json
    return outer


def exception_to_response(exception=None):
    """Construct an HTTPResponse with an HTTP status code determined by
    the passed exception"""
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
