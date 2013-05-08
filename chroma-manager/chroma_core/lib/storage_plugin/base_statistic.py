#
# INTEL CONFIDENTIAL
#
# Copyright 2013 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


from exceptions import ValueError, RuntimeError

DEFAULT_SAMPLE_PERIOD = 10


class BaseStatistic(object):
    """Base class for resource statistics.  When constructing, you may pass in the ``units``
    keyword argument to specify the units of the statistic.  If this is not set, the
    statistic is taken to be a dimensionless numerical quantity.  If this is set to a string
    then this string is used when presenting data to the user.  If this is set to the
    ``UNITS_BYTES`` constant, then values are rounded and formatted as sizes in bytes."""
    UNITS_BYTES = 1

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
