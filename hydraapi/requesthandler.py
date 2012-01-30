#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================
# REST API request handler definitions and other decoratoins
from piston.handler import BaseHandler
from jsonutils import render_to_json
from django.views.decorators.csrf  import csrf_exempt

from hydraapi import api_log


def extract_request_args(f):
    """Decorator to catch boto exceptions and convert them
    to simple exceptions with slightly nicer error messages.
    """
    import functools

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
    import functools

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


class RequestHandler(BaseHandler):
    #allowed_methods = ('GET', 'POST')
    allowed_methods = ('GET')

    def __init__(self):
        BaseHandler.__init__(self)

    def read(self, request):
        """Serve GET requests from the client. It calls the registered function with the GET parameters
        :param request: A HTTP GET request
        """

        if self.run is None:
            raise Exception("No function registered! Unable to process request.")
        request.data = request.GET
        return extract_request_args(self.run)(request)

    def create(self, request):
        return extract_request_args(self.run)(request)


class AnonymousRequestHandler(RequestHandler):
    allowed_methods = ('GET', 'POST')

    def __init__(self, *args, **kwargs):
        RequestHandler.__init__(self)

    @render_to_json()
    @extract_exception
    def read(self, request):
        return RequestHandler.read(self, request)

    @render_to_json()
    @extract_exception
    def create(self, request):
        return RequestHandler.create(self, request)


class AuthorisedRequestHandler(RequestHandler):
    allowed_methods = ('GET', 'POST')

    def __init__(self, registered_function, *args, **kwargs):
        RequestHandler.__init__(self, registered_function)

    @render_to_json()
#    @login_required # This will be rquired when we will need session management
    def read(self, request):
        return RequestHandler.read(self, request)

    @csrf_exempt
    @render_to_json()
#    @login_required # This will be required when we will need session management
    def create(self, request):
        return RequestHandler.create(self, request)


class AnonymousRESTRequestHandler(BaseHandler):
    allowed_methods = ('GET', 'PUT', 'POST', 'DELETE')

    def __init__(self, *args, **kwargs):
        BaseHandler.__init__(self)

    @render_to_json()
    @extract_exception
    def read(self, request, *args, **kwargs):
        request.data = request.GET
        return extract_request_args(self.get)(request, *args, **kwargs)

    @render_to_json()
    @extract_exception
    def create(self, request, *args, **kwargs):
        return extract_request_args(self.post)(request, *args, **kwargs)

    @render_to_json()
    @extract_exception
    def update(self, request, *args, **kwargs):
        return extract_request_args(self.put)(request, *args, **kwargs)

    @render_to_json()
    @extract_exception
    def delete(self, request, *args, **kwargs):
        return extract_request_args(self.remove)(request, *args, **kwargs)


class APIResponse:
    def __init__(self, content, status):
        self.content = content
        self.status = status
