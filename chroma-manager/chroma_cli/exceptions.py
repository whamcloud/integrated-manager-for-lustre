#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


class CliException(Exception):
    pass


class BadRequest(CliException):
    """
    Represents a failed TastyPie validation.
    """
    def __init__(self, value):
        self.error_dict = value
        super(BadRequest, self).__init__()

    def __str__(self):
        errors = ["  %s: %s" % (field, ",".join(errors))
                  for field, errors in self.error_dict.items()]
        return "\n".join(errors)


class InternalError(CliException):
    """
    HTTP 500
    """
    def __init__(self, backtrace):
        self.backtrace = backtrace
        super(InternalError, self).__init__()

    def __str__(self):
        return self.backtrace
