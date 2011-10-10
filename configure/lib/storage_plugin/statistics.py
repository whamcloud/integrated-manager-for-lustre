
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

DEFAULT_SAMPLE_PERIOD = 10

class BaseStatistic(object):
    def __init__(self, sample_period = DEFAULT_SAMPLE_PERIOD):
        self.sample_period = sample_period
        print "BaseStatistic %s" % sample_period

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

    def validate(self, value):
        if len(value) != len(self.bins):
            raise RuntimeError("Invalid histogram value, got %d bins, expected %d" % 
                    len(value), len(self.bins))
