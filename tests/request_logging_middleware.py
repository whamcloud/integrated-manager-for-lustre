import json
import os

from django.conf import settings

from chroma_core.services.log import custom_log_register
from emf_common.lib.date_time import EMFDateTime

REQUEST_LOG_PATH = os.path.join(settings.LOG_PATH, "requests.log")
logger = custom_log_register(__name__, REQUEST_LOG_PATH, False)

TYPES = {"JSON": "application/json", "HTML": "text/html"}


class RequestLoggingMiddleware(object):
    """
    When the log level is in debug mode it should log all request / response pairs.
    If the log level is > DEBUG it does not log the request, response body or their headers.
    """

    def process_response(self, request, response):
        content_type = response["Content-Type"]

        if not any(x in content_type for x in TYPES.values()):
            return response

        def get_meta(prop):
            return request.META.get(prop, "")

        def try_loads(string, default):
            if TYPES["JSON"] not in content_type:
                return default

            try:
                return json.loads(string)
            except ValueError:
                return default

        request_data = {
            "status": response.status_code,
            "content_length": get_meta("CONTENT_LENGTH"),
            "user_agent": get_meta("HTTP_USER_AGENT").decode("utf-8", "replace"),
            "body": try_loads(request.body, ""),
            "response": try_loads(response.content, response.content),
            "request_headers": dict([(key, val) for key, val in request.META.items() if key.isupper()]),
            "response_headers": dict([(key.upper().replace("-", "_"), val) for key, val in response.items()]),
            # The following are required by Bunyan.
            "hostname": get_meta("HTTP_X_FORWARDED_HOST"),
            "name": "Request Log",
            "time": EMFDateTime.utcnow().isoformat(),
            "v": 0,
            "pid": os.getpid(),
            "msg": "Request made to {0} {1}".format(request.method, request.get_full_path()),
            # Bunyan log level is python's log level + 10
            "level": settings.LOG_LEVEL + 10,
        }

        logger.debug(json.dumps(request_data))

        return response
