# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from exceptions import ValueError, RuntimeError

DEFAULT_SAMPLE_PERIOD = 10


class BaseStatistic(object):
    """Base class for resource statistics.  When constructing, you may pass in the ``units``
    keyword argument to specify the units of the statistic.  If this is not set, the
    statistic is taken to be a dimensionless numerical quantity.  If this is set to a string
    then this string is used when presenting data to the user.  If this is set to the
    ``UNITS_BYTES`` constant, then values are rounded and formatted as sizes in bytes."""

    UNITS_BYTES = 1

    def __init__(self, sample_period=DEFAULT_SAMPLE_PERIOD, units=None, label=None):
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
        elif self.units == self.UNITS_BYTES:
            from chroma_core.lib.util import sizeof_fmt_detailed

            return sizeof_fmt_detailed(value)
        else:
            return "%s%s" % (value, self.units)

    def get_unit_name(self):
        if self.units == None:
            return ""
        elif self.units == self.UNITS_BYTES:
            return "bytes"
        else:
            return self.units

    def validate(self, value):
        float(value)  # raises ValueError
