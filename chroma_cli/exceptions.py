# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================


class CliException(Exception):
    pass


class BadRequest(CliException):
    """
    Represents a failed TastyPie validation.
    """
    def __init__(self, value):
        self.error_dict = value

    def __str__(self):
        errors = ["  %s: %s" % (field, ",".join(errors))
                  for field, errors in self.error_dict.items()]
        return "\n".join(errors)
