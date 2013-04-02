#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from django.db import models


# Fields still required for migrations
class PickledObjectField(models.Field):
    __metaclass__ = models.SubfieldBase


class SciFloatField(models.FloatField):
    __metaclass__ = models.SubfieldBase
