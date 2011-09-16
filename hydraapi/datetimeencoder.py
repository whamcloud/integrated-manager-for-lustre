#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================
#
from django.core.serializers.json import DateTimeAwareJSONEncoder
# Place holder class we might require this for UTC format dates
# in monitoring data.
class DjangoTimeJSONEncoder(DateTimeAwareJSONEncoder):
    """
    JSONEncoder subclass that knows how to encode date/time.
    """

    DATE_FORMAT = "%Y-%m-%d"
    TIME_FORMAT = "%H:%M:%S"

    def encode(self, request, o):
        return DateTimeAwareJSONEncoder().encode(o)
