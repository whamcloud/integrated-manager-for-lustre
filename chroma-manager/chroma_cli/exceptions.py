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
    pass


class BadRequest(ApiException):
    """
    Represents a failed TastyPie validation.
    """
    def __init__(self, value):
        self.error_dict = value
        super(BadRequest, self).__init__()

    def __str__(self):
        lines = []
        for field, errors in self.error_dict.items():
            for error in errors:
                lines.extend(["  %s: %s" % (field, error)])
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
    pass
