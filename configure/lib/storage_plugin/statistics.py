
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================


"""This module defines ResourceStatistic and subclasses"""

class ResourceStatistic(object):
    pass

class GaugeStatistic(ResourceStatistic):
    def r3d_type(self):
        return 'Gauge'

class CounterStatistic(ResourceStatistic):
    def r3d_type(self):
        return 'Counter'

    
