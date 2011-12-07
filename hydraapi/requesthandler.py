#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================
# REST API request handler definitions and other decoratoins
from piston.handler import BaseHandler
from jsonutils import render_to_json
from django.views.decorators.csrf  import csrf_exempt

import settings

import logging
hydraapi_log = logging.getLogger('hydraapi')
handler = logging.FileHandler(settings.API_LOG_PATH)
handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', '%d/%b/%Y:%H:%M:%S'))
hydraapi_log.addHandler(handler)


if settings.DEBUG:
    hydraapi_log.setLevel(logging.DEBUG)
else:
    hydraapi_log.setLevel(logging.WARNING)


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
            hydraapi_log.info("API call %s(%s)" % (f.__name__, ", ".join(map(repr, params))))
            return f(*args, **kwds)
        except Exception:
            import sys
            import traceback
            hydraapi_log.error("API error %s(%s)" % (f.__name__, ", ".join(map(repr, params))))
            hydraapi_log.error("\n".join(traceback.format_exception(*(sys.exc_info()))))
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
        return self.run(request)

    def create(self, request):
        return self.run(request)


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


class extract_request_args:
    """Extracts specified keys from the request dictionary and calls the wrapped
    function
    """
    def __init__(self, *args):
        self.args = args

    def __call__(self, f):
        def wrapped_f(wrapped_self, request):
            # This will be rquired for session management
            #if request.session:
            #    request.session.set_expiry(request.user.get_inactivity_timeout())
            import urllib2
            call_args = {}
            data = request.data
            errors = {}
            #Fill in the callArgs with values from the request data
            for value in self.args:
                try:
                    call_args[value] = data[value]
                except:
                    errors[value] = ["This field is required."]
                    pass

            if len(errors) > 0:
                raise urllib2.URLError(errors)
            return f(wrapped_self, request, **call_args)
        return wrapped_f


class APIResponse:
    HTTP_SUCCESS_CODES = dict(ALL_OK = 200,
                              CREATED = 201,
                              ACCEPTED = 202,
                              NON_AUTH = 203,
                              DELETED = 204,
                              RESET_CONTENT = 205,
                              PARTIAL_CONTENT = 206)
    content = None

    def __init__(self, content, status):
        status = self.HTTP_SUCCESS_CODES.get(self.HTTP_SUCCESS_CODES.ALL_OK)
        if status not in self.HTTP_SUCCESS_CODES.values():
            raise Exception("Invalid HTTP success status code: unable to create APIResponse")
        self.content = content
        self.status = status
