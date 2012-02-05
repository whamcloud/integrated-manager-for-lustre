#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================


import urllib2
import functools
from piston.handler import BaseHandler
from django.http import HttpResponse
from django.core.serializers.json import DateTimeAwareJSONEncoder
import django.utils.cache

from chroma_api import api_log


def render_to_json(**jsonargs):
    """
    Run the wrapped function, and:
     * If it throws an exception, generate an HTTP response with appropriate error status code
     * If it returns an APIResponse, use the status_code and content to populate an HTTP response
     * Else, return an HTTP response with the return value JSON encoded and a status of 200
    """
    def outer(f):
        @functools.wraps(f)
        def inner_json(wrapped_self, request, *args, **kwargs):
            r = HttpResponse(mimetype='application/json')
            errors = None
            try:
                from hydraapi.requesthandler import APIResponse
                result = f(wrapped_self, request, *args, **kwargs)
                if isinstance(result, APIResponse):
                    r.status_code = result.status
                    if result.cache == False:
                        django.utils.cache.add_never_cache_headers(r)
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


def extract_request_args(f):
    """Decorator to catch boto exceptions and convert them
    to simple exceptions with slightly nicer error messages.
    """
    @functools.wraps(f)
    def _extract_request_args(request, *args, **kwargs):
        # This will be rquired for session management
        #if request.session:
        #    request.session.set_expiry(request.user.get_inactivity_timeout())

        import inspect
        arg_spec = inspect.getargspec(f)

        # First two arguments are 'self' and 'request', skip them
        arg_names = arg_spec[0][2:]

        # Build a map of any default values for arguments
        defaults_list = arg_spec[3]
        defaults = {}
        if defaults_list:
            #eg:
            # fn prototype a, b=1, c=2
            #  arg_names (a,b,c)
            #  defaults_list (1,2)
            for i in range(0, len(defaults_list)):
                defaults[arg_names[-len(defaults_list) + i]] = defaults_list[i]

        errors = {}
        # Turn passed-through *args into a list so that we can append to it
        args = list(args)
        for arg_name in arg_names:
            if arg_name in kwargs:
                # Already got a value of the argument from passed-through kwargs
                continue

            if isinstance(request.data, dict):
                if arg_name in defaults:
                    # This is a keyword argument
                    try:
                        kwargs[arg_name] = request.data[arg_name]
                    except KeyError:
                        kwargs[arg_name] = defaults[arg_name]
                else:
                    # This is a positional argument
                    try:
                        args.append(request.data[arg_name])
                    except KeyError:
                        errors[arg_name] = ["This field is required"]
            else:
                # Request.data is not a dict -- no arguments supplied
                if arg_name in defaults:
                    kwargs[arg_name] = defaults[arg_name]
                else:
                    errors[arg_name] = ["This field is required"]

        if len(errors) > 0:
            # FIXME: random abuse of URLError -- should define an
            # exception class that really means invalid request
            import urllib2
            raise urllib2.URLError(errors)

        return f(request, *args, **kwargs)

    return _extract_request_args


def extract_exception(f):
    """Decorator to catch boto exceptions and convert them
    to simple exceptions with slightly nicer error messages.
    """

    @functools.wraps(f)
    def _extract_exception(*args, **kwds):
        from itertools import chain
        from django.http import HttpRequest
        params = chain([a for a in args if not isinstance(a, HttpRequest)], kwds.values())
        try:
            api_log.info("API call %s(%s)" % (f.__name__, ", ".join(map(repr, params))))
            return f(*args, **kwds)
        except Exception:
            import sys
            import traceback
            api_log.error("API error %s(%s)" % (f.__name__, ", ".join(map(repr, params))))
            api_log.error("\n".join(traceback.format_exception(*(sys.exc_info()))))
            raise
    return _extract_exception


class APIResponse:
    def __init__(self, content, status, cache = True):
        self.content = content
        self.status = status
        self.cache = cache


class RequestHandler(BaseHandler):
    allowed_methods = ('GET', 'PUT', 'POST', 'DELETE')

    def __init__(self, *args, **kwargs):
        BaseHandler.__init__(self)

    def _call_wrapped(self, handler_fn_name, request, *args, **kwargs):
        try:
            handler_fn = getattr(self, handler_fn_name)
        except AttributeError:
            return APIResponse(None, 405)
        return extract_request_args(handler_fn)(request, *args, **kwargs)

    @render_to_json()
    @extract_exception
    def read(self, request, *args, **kwargs):
        request.data = request.GET
        return self._call_wrapped('get', request, *args, **kwargs)

    @render_to_json()
    @extract_exception
    def create(self, request, *args, **kwargs):
        return self._call_wrapped('post', request, *args, **kwargs)

    @render_to_json()
    @extract_exception
    def update(self, request, *args, **kwargs):
        return self._call_wrapped('put', request, *args, **kwargs)

    @render_to_json()
    @extract_exception
    def delete(self, request, *args, **kwargs):
        # FIXME: it's rather confusing to have 'remove' when
        # all the other functions are named after their HTTP verbs (it is
        # this way because django piston uses 'delete' here where it
        # uses non-verb-named methods for the others.
        return self._call_wrapped('remove', request, *args, **kwargs)
