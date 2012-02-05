
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

DEFAULT_SAMPLE_PERIOD = 10

UNITS_BYTES = 1


class BaseStatistic(object):
    """Base class for resource statistics.  When constructing, you may pass in the ``units``
    keyword argument to specify the units of the statistic.  If this is not set, the
    statistic is taken to be a dimensionless numerical quantity.  If this is set to a string
    then this string is used when presenting data to the user.  If this is set to the
    ``UNITS_BYTES`` constant, then values are rounded and formatted as sizes in bytes."""
    def __init__(self, sample_period = DEFAULT_SAMPLE_PERIOD, units = None, label = None):
        """'units' can be None for dimensionless scalars, UNITS_BYTES for
        sizes in bytes, or a string for arbitrary units"""
        try:
            int(sample_period)
        except ValueError:
            raise RuntimeError("sample period '%s' is not an integer!" % sample_period)

        self.sample_period = sample_period
        self.units = units
        self.label = label

    def format_units(self, value):
        if self.units == None:
            return value
        elif self.units == UNITS_BYTES:
            from monitor.lib.util import sizeof_fmt_detailed
            return sizeof_fmt_detailed(value)
        else:
            return "%s%s" % (value, self.units)

    def get_unit_name(self):
        if self.units == None:
            return ""
        elif self.units == UNITS_BYTES:
            return "bytes"
        else:
            return self.units

    def validate(self, value):
        pass


class Gauge(BaseStatistic):
    """A numerical time series which can go up or down"""
    def r3d_type(self):
        return 'Gauge'


class Counter(BaseStatistic):
    """A monotonicall increasing time series."""
    def r3d_type(self):
        return 'Counter'


class BytesHistogram(BaseStatistic):
    """A fixed-length array of integers used for representing histogram data.  The number of
    bins and the value range of each bin is specified in the ``bins`` constructor argument:

    ::

        BytesHistogram(bins = [(0, 512), (513, 1024), (1025, 4096), (4097,)])

    :param bins: a list of tuples, either length 2 for a bounded range or length 1
                 to represent "this value or higher".

    """
    def __init__(self, *args, **kwargs):
        """
        e.g. bins=[(0, 256), (257, 512), (513, 2048), (2049, 4096), (4097,)]
        """
        self.bins = kwargs.pop('bins')

        super(BytesHistogram, self).__init__(*args, **kwargs)

    def format_bin(self, bin):
        return u"\u2264%s" % (self.format_units(bin[1]))

    def validate(self, value):
        if len(value) != len(self.bins):
            raise RuntimeError("Invalid histogram value, got %d bins, expected %d" %
                    len(value), len(self.bins))
