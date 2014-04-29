#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2014 Intel Corporation All Rights Reserved.
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
        self.bins = kwargs.pop('bins')

        super(BytesHistogram, self).__init__(*args, **kwargs)

    def format_bin(self, bin):
        return u"\u2264%s" % (self.format_units(bin[1]))

    def validate(self, value):
        if len(value) != len(self.bins):
            raise ValueError("Invalid histogram value, got %d bins, expected %d" % (len(value), len(self.bins)))
