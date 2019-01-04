# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from chroma_core.lib.storage_plugin.base_statistic import BaseStatistic


class Gauge(BaseStatistic):
    """A numerical time series which can go up or down"""


class Counter(BaseStatistic):
    """A monotonically increasing time series."""


class BytesHistogram(BaseStatistic):
    """A fixed-length array of integers used for representing histogram data.  The number of
    bins and the value range of each bin are specified in the ``bins`` constructor argument:

    ::

        BytesHistogram(bins = [(0, 512), (513, 1024), (1025, 4096), (4097,)])

    :param bins: a list of tuples, either length 2 for a bounded range or length 1
                 to represent "this value or higher".

    """

    def __init__(self, *args, **kwargs):
        """
        e.g. bins=[(0, 256), (257, 512), (513, 2048), (2049, 4096), (4097,)]
        """
        self.bins = kwargs.pop("bins")

        super(BytesHistogram, self).__init__(*args, **kwargs)

    def format_bin(self, bin):
        return u"\u2264%s" % (self.format_units(bin[1]))

    def validate(self, value):
        if len(value) != len(self.bins):
            raise ValueError("Invalid histogram value, got %d bins, expected %d" % (len(value), len(self.bins)))
