
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

DEFAULT_SAMPLE_PERIOD = 10

UNITS_BYTES = 1

class BaseStatistic(object):
    def __init__(self, sample_period = DEFAULT_SAMPLE_PERIOD, units = None):
        """'units' can be None for dimensionless scalars, UNITS_BYTES for
        sizes in bytes, or a string for arbitrary units"""
        self.sample_period = sample_period
        self.units = units
        print "BaseStatistic %s" % sample_period

    def format_units(self, value):
        if self.units == None:
            return value
        elif self.units == UNITS_BYTES:
            from monitor.lib.util import sizeof_fmt_detailed
            return sizeof_fmt_detailed(value)
        else:
            return "%s%s" % (value, self.units)

    def validate(self, value):
        pass

class Gauge(BaseStatistic):
    def r3d_type(self):
        return 'Gauge'

class Counter(BaseStatistic):
    def r3d_type(self):
        return 'Counter'

class BytesHistogram(BaseStatistic):
    def __init__(self, *args, **kwargs):
        """
        e.g. bins=[(0,256), (257, 512), (513, 2048), (2049, 4096), (4097,)]
        """
        self.bins = kwargs.pop('bins')

        super(BytesHistogram, self).__init__(*args, **kwargs)

    def format_bin(self, bin):
        return u"\u2264%s" % (self.format_units(bin[1]))
    
    def validate(self, value):
        if len(value) != len(self.bins):
            raise RuntimeError("Invalid histogram value, got %d bins, expected %d" % 
                    len(value), len(self.bins))
