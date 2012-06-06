#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


class ApiException(Exception):
    pass


class InvalidApiResource(ApiException):
    def __init__(self, name):
        self.error_str = "Invalid API Resource: %s" % name

    def __str__(self):
        return self.error_str


class UnsupportedFormat(ApiException):
    pass


class TooManyMatches(ApiException):
    """
    Too many matches returned during a fuzzy-id lookup.
    """
    def __str__(self):
        return "The query matched more than one record."


class InvalidVolumeNode(ApiException):
    def __init__(self, input):
        self.input = input

    def __str__(self):
        return "Invalid VolumeNode spec: %s (malformed or bad path?)" % self.input


class BadUserInput(ApiException):
    """
    Generic exception for bad user input detected post-argparse.
    """
    pass


class BadRequest(ApiException):
    """
    Represents a failed TastyPie validation or other 400-level error.
    """
    def __init__(self, value):
        self.error_dict = value
        super(BadRequest, self).__init__()

    def __str__(self):
        lines = ["The server rejected the request with the following error(s):"]
        try:
            for field, errors in self.error_dict.items():
                for error in errors:
                    lines.extend(["  %s: %s" % (field, error)])
        except AttributeError:
            # Sometimes what comes back is just a string.
            lines.append(self.error_dict)
        return "\n".join(lines)


class InternalError(ApiException):
    """
    HTTP 500
    """
    def __init__(self, backtrace):
        self.backtrace = backtrace
        super(InternalError, self).__init__()

    def __str__(self):
        return self.backtrace


class NotFound(ApiException):
    """
    HTTP 404
    """
    pass


class UnauthorizedRequest(ApiException):
    """
    HTTP 401
    """
    pass


class AuthenticationFailure(ApiException):
    """
    HTTP 401 after trying to authenticate.
    """


class ApiConnectionError(ApiException):
    def __init__(self, api_url):
        self.api_url = api_url

    def __str__(self):
        return "Failed to connect to %s (is --api_url correct?)" % self.api_url
