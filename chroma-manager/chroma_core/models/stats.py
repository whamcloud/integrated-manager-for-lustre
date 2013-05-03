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


import itertools
import collections
import calendar
import operator
import functools
from datetime import datetime, timedelta
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.utils.timezone import utc


__all__ = 'Point', 'Series', 'Stats'


def total_seconds(td):
    "Return timedelta.total_seconds (builtin in 2.7)"
    return (td.days * 24 * 60 * 60) + td.seconds

ROWS = 1000  # sample size multiplier for total number of rows
SAMPLES = {'seconds': 10}, {'minutes': 1}, {'minutes': 5}, {'hours': 1}, {'days': 1}
SAMPLES = tuple(total_seconds(timedelta(**SAMPLE)) for SAMPLE in SAMPLES)
for div, mod in map(divmod, SAMPLES[1:], SAMPLES[:-1]):
    assert div > 1 and mod == 0, SAMPLES


class Point(collections.namedtuple('Point', ('dt', 'sum', 'len'))):
    "Fast and small tuple wrapper for a single data point."
    __slots__ = ()

    @property
    def mean(self):
        return self.len and self.sum / self.len

    @property
    def timestamp(self):
        return calendar.timegm(self.dt.utctimetuple())

    def __add__(self, other):
        return type(self)(self.dt, self.sum + other.sum, self.len + other.len)

    def __sub__(self, other):
        return type(self)(self.dt, self.mean - other.mean, total_seconds(self.dt - other.dt))

epoch = datetime.fromtimestamp(0, utc)
Point.zero = Point(epoch, 0.0, 0)


class Series(models.Model):
    """Sources and their associated fields.
    Leverages the ContentTypes framework to allow series to be associated with other apps' models.
    """
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=30)
    content_object = generic.GenericForeignKey('content_type', 'object_id')

    class Meta:
        app_label = 'chroma_core'
        unique_together = ('content_type', 'object_id', 'name'),

    cache = {}

    @classmethod
    def get(cls, obj, name, type=''):
        "Return cached series for measured object and field, optionally creating it with given type."
        try:
            return cls.cache[obj, name]
        except KeyError:
            ct = ContentType.objects.get_for_model(obj)
        if type:
            series, created = Series.objects.get_or_create(content_type=ct, object_id=obj.id, name=name, type=type)
        else:
            series = Series.objects.get(content_type=ct, object_id=obj.id, name=name)
        return cls.cache.setdefault((obj, name), series)


class Sample(models.Model):
    """Abstract model for Sample tables.
    Only used for query generation.
    Subclasses require 'step', 'expiration', and 'cache' attributes.
    """
    id = models.IntegerField(primary_key=True)  # for django only, not really the primary key
    dt = models.DateTimeField()
    sum = models.FloatField()
    len = models.IntegerField()

    class Meta:
        abstract = True
        unique_together = ('id', 'dt'),

    @classmethod
    def latest(cls, id):
        "Return most recent data point for series."
        return (cls.cache[id] or list(cls.select(id, order_by='-dt', limit=1)) or [Point.zero])[-1]

    @classmethod
    def start(cls, id):
        "Return earliest datetime that should be stored for series."
        try:
            return cls.latest(id).dt - cls.expiration
        except OverflowError:
            return epoch

    @classmethod
    def floor(cls, point):
        "Return point's datetime rounded down to nearest sample size."
        return point.dt - timedelta(seconds=point.timestamp % cls.step, microseconds=point.dt.microsecond)

    @classmethod
    def reduce(cls, points):
        "Generate points grouped and summed by sample size."
        for dt, points in itertools.groupby(points, key=cls.floor):
            yield Point(dt, *sum(points, Point.zero)[1:])

    @classmethod
    def select(cls, id, order_by='dt', limit=None, **filters):
        "Generate points for a series."
        query = cls.objects.filter(id=id, **filters).order_by(order_by)[:limit]
        return itertools.starmap(Point, query.values_list(*Point._fields))

    @classmethod
    def insert(cls, stats):
        "Bulk insert mapping of series ids to points."
        if stats:
            cls.objects.bulk_create(cls(id, *point) for id in stats for point in stats[id])
        for id in stats:
            cls.cache[id] += sorted(stats[id])

    @classmethod
    def delete(cls, **filters):
        "Delete points in bulk."
        query = cls.objects.filter(**filters)
        # QuerySet.delete doesn't delete in bulk, documentation notwithstanding
        models.sql.DeleteQuery(cls).do_query(cls._meta.db_table, query.query.where, query.db)

    @classmethod
    def expire(cls, ids):
        "Delete earliest points from multiple series."
        if ids:
            cls.delete(id__in=ids, dt__lt=min(map(cls.start, ids)))


class Stats(list):
    "Primary interface to all sample models."
    def __init__(self, samples, rows):
        maxlen = max(map(operator.floordiv, samples[1:], samples[:-1]))
        for sample in samples:
            cache = collections.defaultdict(functools.partial(collections.deque, maxlen=maxlen))
            namespace = {'__module__': 'chroma_core.models', 'step': sample, 'expiration': timedelta(seconds=rows * sample * sample), 'cache': cache}
            self.append(type('Sample_{0:d}'.format(sample), (Sample,), namespace))

    def insert(self, samples):
        "Bulk insert new samples (id, dt, value).  Skip and return outdated samples."
        # keep stats as Points grouped by id
        outdated, stats = [], collections.defaultdict(list)
        for id, dt, value in samples:
            if dt > self[0].latest(id).dt:
                stats[id].append(Point(dt, value, 1))
            else:
                outdated.append((id, dt, value))
        # insert stats into first Sample and check the rest
        self[0].insert(stats)
        for previous, model in zip(self, self[1:]):
            step = timedelta(seconds=model.step)
            for id in list(stats):
                start = model.latest(id).dt + step
                stop = model.floor(max(stats.pop(id)))
                cache = previous.cache[id]
                # aggregate from previous Sample as necessary
                if start < stop:
                    if cache and start >= cache[0].dt and stop <= cache[-1].dt:  # use cache if full
                        points = (point for point in cache if start <= point.dt < stop and point.len)
                    else:
                        points = previous.select(id, dt__gte=start, dt__lt=stop)
                    points = list(model.reduce(points))
                    if points:
                        stats[id] = points
                    else:  # ensure query isn't repeated on cache miss
                        model.cache[id].append(Point(stop - step, 0.0, 0))
            previous.expire(stats)
            model.insert(stats)
        model.expire(stats)
        return outdated

    def select(self, id, start, stop, rate=False, maxlen=float('inf')):
        """Return points for a series within inclusive interval of most granular samples.
        Optionally derive the rate of change of points.
        Optionally limit number of points by increasing sample resolution.
        """
        minstep = total_seconds(stop - start) / maxlen
        for index, model in enumerate(self):
            if start >= model.start(id) and model.step >= minstep:
                break
        points = model.select(id, dt__gte=start, dt__lte=stop)
        points = list(points if index else model.reduce(points))
        return map(operator.sub, points[1:], points[:-1]) if rate else points

    def latest(self, id):
        "Return most recent data point."
        point = self[0].latest(id)
        return Point(self[0].floor(point), *point[1:])

    def delete(self, id):
        "Delete all stored points for a series."
        for model in self:
            model.delete(id=id)

Stats = Stats(SAMPLES, ROWS)
