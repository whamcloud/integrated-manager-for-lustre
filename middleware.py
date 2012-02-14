

import traceback
import sys

from chroma_api import api_log

from django.http import HttpResponse
import json
import settings


class ExceptionFormatterMiddleware:
    def process_exception(self, request, exception):
        exc_info = sys.exc_info()
        traceback_str = '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))

        api_log.error("######################## Exception #############################")
        api_log.error(traceback_str)
        api_log.error("################################################################")

        if request.META['HTTP_ACCEPT'] == "application/json":
            if settings.DEBUG:
                report = {
                    'error_message': str(exception),
                    'traceback': traceback_str
                    }
            else:
                report = {
                    'error_message': "Sorry, this request could not be processed.  Please try again later."
                    }
            # For JSON requests, return a serialized exception
            # instead of rendering an HTML 500 page
            return HttpResponse(json.dumps(report), status=500, content_type = "application/json")
        else:
            # Non-JSON request: let django return a default
            # 500 page
            return None
