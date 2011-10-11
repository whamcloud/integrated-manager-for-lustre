#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================
# REST API request handler definitions and other decoratoins
from piston.handler import BaseHandler
from jsonutils import render_to_json
from  django.views.decorators.csrf  import csrf_exempt
#
class RequestHandler(BaseHandler):
    #allowed_methods = ('GET', 'POST')
    allowed_methods = ('GET')
    
    def __init__(self, registered_function, *args, **kwargs):
        BaseHandler.__init__(self)
        self.registered_function = registered_function    
    
    
    def read(self, request):
        """Serve GET requests from the client. It calls the registered function with the GET parameters
        :param request: A HTTP GET request 
        """
        
        if self.registered_function is None:
            raise Exception("No function registered! Unable to process request.")
        #Set the data of the get request to request.data because
        #the base classes will all look in request.data for the data
        #In POST requests this is handled by piston
        request.data = request.GET
        return self.registered_function(request)
    
    def create(self, request):
#        """Serve POST requests from the client. It calls the registered function with the POST parameters
#        :param request: A HTTP POST request           
#        """
#        if self.registered_function is None:
#            raise Exception("No function registered! Unable to process request.")
        return self.registered_function(request)

class AnonymousRequestHandler(RequestHandler):
    
    allowed_methods = ('GET', 'POST')
    
    def __init__(self, registered_function, *args, **kwargs):
        RequestHandler.__init__(self, registered_function)
    
    @render_to_json()
    def read(self, request):
        return RequestHandler.read(self, request)
    
    @render_to_json()
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
    def __init__(self, **kwargs):
        self.args = kwargs
    def __call__(self, f):
        def wrapped_f(wrapped_self, request):
            # This will be rquired for session management
            #if request.session:
            #    request.session.set_expiry(request.user.get_inactivity_timeout())
            call_args = { }
            data = request.data
            errors = { }
            #Fill in the callArgs with values from the request data
            for key,value in self.args.items():
                try:
                    call_args[key] = data[value]
                except:
                    errors[value] = [ "This field is required." ] 
                    pass
                
            if len(errors) > 0:
                raise Exception(errors)
            return f(wrapped_self, request, **call_args)
        return wrapped_f

def extract_exception(f):
    """Decorator to catch boto exceptions and convert them
    to simple exceptions with slightly nicer error messages.
    """
    import settings
    import logging
    hydraapi_log = logging.getLogger('hydraapi')
    hydraapi_log.setLevel(logging.DEBUG)
    handler = logging.FileHandler(settings.API_LOG_PATH)
    handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', '%d/%b/%Y:%H:%M:%S'))
    hydraapi_log.addHandler(handler)
    import functools
    import sys
    @functools.wraps(f)
    def _extract_exception(*args, **kwds):
        try:
            from itertools import chain
            name = f.__name__
            hydraapi_log.info("API_CALL=%s(%s)" % (name, ", ".join(map(repr, chain(args ,kwds.values())))))
            return f(*args, **kwds)
        except Exception as err:
            exc_info = sys.exc_info()
            hydraapi_log.error(err.error_message, exc_info[1], exc_info[2])
            raise Exception(err.error_message + exc_info[1] + exc_info[2])
    return _extract_exception
