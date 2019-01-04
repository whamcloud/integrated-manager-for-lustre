# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


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
from chroma_core.lib.util import chroma_settings

settings = chroma_settings()


__all__ = "Point", "Series", "Stats"


def total_seconds(td):
    "Return timedelta.total_seconds (builtin in 2.7)"
    return (td.days * 24 * 60 * 60) + td.seconds + (td.microseconds * 1e-6)


class SampleInfo(object):
    def __init__(self, sample_rate, expiration_time):
        self.sample_rate = int(total_seconds(timedelta(**sample_rate)))
        self.expiration_time = timedelta(**expiration_time)


SAMPLES = [
    SampleInfo({"seconds": 10}, settings.STATS_10_SECOND_EXPIRATION),
    SampleInfo({"minutes": 1}, settings.STATS_1_MINUTE_EXPIRATION),
    SampleInfo({"minutes": 5}, settings.STATS_5_MINUTE_EXPIRATION),
    SampleInfo({"hours": 1}, settings.STATS_1_HOUR_EXPIRATION),
    SampleInfo({"days": 1}, settings.STATS_1_DAY_EXPIRATION),
]


def div_samplerate(x, y):
    div, mod = divmod(x.sample_rate, y.sample_rate)
    assert div > 1 and mod == 0

    return div


def timestamp(dt):
    "Return utc timestamp from datetime."
    return calendar.timegm(dt.utctimetuple())


class Point(collections.namedtuple("Point", ("dt", "sum", "len"))):
    "Fast and small tuple wrapper for a single data point."
    __slots__ = ()

    @property
    def mean(self):
        return self.len and self.sum / self.len

    @property
    def timestamp(self):
        return timestamp(self.dt)

    def __add__(self, other):
        return type(self)(self.dt, self.sum + other.sum, self.len + other.len)

    def __sub__(self, other):
        return type(self)(self.dt, self.mean - other.mean, total_seconds(self.dt - other.dt))


epoch = datetime.fromtimestamp(0, utc)
Point.zero = Point(epoch, 0.0, 0)


class Cache(collections.defaultdict):
    "Simple cache of limited size;  doesn't need to be LRU yet."
    SIZE = 1e5

    def __setitem__(self, key, value):
        collections.defaultdict.__setitem__(self, key, value)
        if len(self) > self.SIZE:
            self.clear()


class Series(models.Model):
    """Sources and their associated fields.
    Leverages the ContentTypes framework to allow series to be associated with other apps' models.
    """

    DATA_TYPES = "Gauge", "Counter", "Derive"
    JOB_TYPES = "SLURM_JOB_ID", "JOB_ID", "LSB_JOBID", "LOADL_STEP_ID", "PBS_JOBID", "procname_uid"
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=30)
    content_object = generic.GenericForeignKey("content_type", "object_id")

    class Meta:
        app_label = "chroma_core"
        unique_together = (("content_type", "object_id", "name"),)

    cache = Cache(None)

    @classmethod
    def get(cls, obj, name, type=""):
        "Return cached series for measured object and field, optionally creating it with given type."
        try:
            return cls.cache[obj, name]
        except KeyError:
            ct = ContentType.objects.get_for_model(obj)
        if type:
            assert type in cls.DATA_TYPES + cls.JOB_TYPES
            series, created = cls.objects.get_or_create(content_type=ct, object_id=obj.id, name=name, type=type)
        else:
            series = cls.objects.get(content_type=ct, object_id=obj.id, name=name)
        cls.cache[obj, name] = series
        return series

    @classmethod
    def filter(cls, obj, **kwargs):
        "Return queryset filtered for measured object."
        ct = ContentType.objects.get_for_model(obj)
        return cls.objects.filter(content_type=ct, object_id=obj.id, **kwargs)


class Sample(models.Model):
    """Abstract model for Sample tables.
    Only used for query generation.
    Subclasses require 'step', 'expiration_time', and 'cache' attributes.
    """

    id = models.IntegerField(primary_key=True)  # for django only, not really the primary key
    dt = models.DateTimeField(db_index=True)
    sum = models.FloatField()
    len = models.IntegerField()

    class Meta:
        abstract = True
        unique_together = (("id", "dt"),)

    @classmethod
    def latest(cls, id):
        "Return most recent data point for series."
        return (cls.cache[id] or list(cls.select(id, order_by="-dt", limit=1)) or [Point.zero])[-1]

    @classmethod
    def start(cls, id):
        "Return earliest datetime that should be stored for series."
        try:
            return cls.latest(id).dt - cls.expiration_time
        except OverflowError:
            return epoch

    @classmethod
    def floor(cls, dt):
        "Return datetime rounded down to nearest sample size."
        return dt - timedelta(seconds=timestamp(dt) % cls.step, microseconds=dt.microsecond)

    @classmethod
    def reduce(cls, points_to_reduce):
        "Generate points grouped and summed by sample size."
        for dt, points in itertools.groupby(points_to_reduce, key=lambda point: cls.floor(point.dt)):
            yield Point(dt, *sum(points, Point.zero)[1:])

    @classmethod
    def select(cls, id, order_by="dt", limit=None, **filters):
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
        if settings.STATS_SIMPLE_WIPE:
            "We also have a general flush added in for 2.2 which just clears everything old every so often!"
            now = datetime.now(utc)
            if now > cls.next_flush_orphans_time:
                cls.delete(dt__lt=now - cls.expiration_time)
                cls.next_flush_orphans_time = now + cls.flush_orphans_interval
        else:
            "Delete earliest points from multiple series."
            if ids:
                cls.delete(id__in=ids, dt__lt=min(map(cls.start, ids)))


class Stats(list):
    "Primary interface to all sample models."

    def __init__(self, samples):
        maxlen = max(map(div_samplerate, samples[1:], samples[:-1]))
        for sample in samples:
            cache = Cache(functools.partial(collections.deque, maxlen=maxlen))
            namespace = {
                "__module__": "chroma_core.models",
                "step": sample.sample_rate,
                "expiration_time": sample.expiration_time,
                "next_flush_orphans_time": epoch,
                "flush_orphans_interval": sample.expiration_time / settings.STATS_FLUSH_RATE,
                "cache": cache,
            }
            self.append(type("Sample_{0:d}".format(sample.sample_rate), (Sample,), namespace))

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
                stop = model.floor(max(stats.pop(id)).dt)
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
            previous.expire(stats)
            model.insert(stats)
        model.expire(stats)
        return outdated

    def select(self, id, start, stop, rate=False, maxlen=float("inf"), fixed=0):
        """Return points for a series within inclusive interval of most granular samples.
        Optionally derive the rate of change of points.
        Optionally limit number of points by increasing sample resolution.
        Optionally return fixed intervals with padding and arbitrary resolution.
        """
        minstep = total_seconds(stop - start) / maxlen
        for index, model in enumerate(self):
            if start >= model.start(id) and model.step >= minstep:
                break
        points = model.select(id, dt__gte=start, dt__lt=stop)
        points = list(points if index else model.reduce(points))
        if rate:
            points = map(operator.sub, points[1:], points[:-1])
        if fixed:
            step = (stop - start) / fixed
            intervals = [Point(start + step * index, 0.0, 0) for index in range(fixed)]
            for point in points:
                intervals[int(total_seconds(point.dt - start) / total_seconds(step))] += point
            points = intervals
        return points

    def latest(self, id):
        "Return most recent data point."
        point = self[0].latest(id)
        return Point(self[0].floor(point.dt), point.sum, point.len)

    def delete(self, id):
        "Delete all stored points for a series."
        for model in self:
            model.delete(id=id)

    def delete_all(self):
        "Delete all stored points for a series."
        for model in self:
            model.delete(id__gte=0)


Stats = Stats(SAMPLES)
