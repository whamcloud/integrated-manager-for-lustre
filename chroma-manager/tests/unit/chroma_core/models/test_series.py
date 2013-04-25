#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import random
import calendar
from datetime import datetime, timedelta
from django.utils.timezone import utc
from django.test import TestCase
from django.contrib.auth.models import User
from chroma_core.lib import metrics
from chroma_core.models import Series, Stats

fields = ('size', 'Gauge', 0, 1000), ('bandwith', 'Counter', 0, 100), ('speed', 'Derive', -100, 100)
epoch = datetime.fromtimestamp(0, utc)


def timestamp(dt):
    return calendar.timegm(dt.utctimetuple())


def gen_series(sample, rows):
    "Generate sample timestamps and randomized data."
    for index in xrange(rows):
        yield (index * sample), dict((field[0], {'type': field[1], 'value': random.randint(*field[2:])}) for field in fields)


class TestSeries(TestCase):
    "Test series updates and fetches at the MetricStore layer"

    def setUp(self):
        self.obj = User.objects.create(username='test', email='test@test.test')
        self.store = metrics.MetricStore(self.obj)

    def tearDown(self):
        self.store.clear()
        self.obj.delete()

    def test_integrity(self):
        field, type = fields[0][:2]
        series = Series.get(self.obj, field, type)
        self.assertIs(series, Series.get(self.obj, field))
        Series.cache.clear()
        self.assertEqual(series, Series.get(self.obj, field))

    def test_fast(self):
        "Small data set with short intervals."
        for data in zip(*[gen_series(5, 100)] * 10):
            Stats.insert(self.store.serialize(dict(data)))
        names = [field[0] for field in fields]
        latest, data = self.store.fetch_last(names)
        self.assertEqual(timestamp(latest), 490)
        for name, type, start, stop in fields:
            self.assertGreaterEqual(data[name], start)
            self.assertLessEqual(data[name], stop)
        stats = self.store.fetch(names[:1], epoch, epoch + timedelta(seconds=10))
        self.assertEqual(len(stats), 2)
        dt = min(stats)
        data = stats[dt]
        self.assertEqual(dt, epoch)
        for name, type, start, stop in fields:
            if type == 'Gauge':
                self.assertGreaterEqual(data[name], start)
                self.assertLessEqual(data[name], stop)
            else:
                self.assertNotIn(name, data)
        stats = self.store.fetch(names, epoch, epoch + timedelta(seconds=10))
        self.assertEqual(len(stats), 1)
        dt = min(stats)
        data = stats[dt]
        self.assertEqual(timestamp(dt), 10)
        for name, type, start, stop in fields:
            if type == 'Gauge':
                self.assertGreaterEqual(data[name], start)
                self.assertLessEqual(data[name], stop)
            else:
                delta = (stop - start) / 10.0
                self.assertGreaterEqual(data[name], -delta)
                self.assertLessEqual(data[name], delta)

    def test_slow(self):
        "Large data set with long intervals."
        rows = 1100
        for data in zip(*[gen_series(100, rows)] * 10):
            Stats.insert(self.store.serialize(dict(data)))
        names = [field[0] for field in fields]
        latest, data = self.store.fetch_last(names)
        for seconds, model in zip((1e4, 5e4, 1e5, 1e6, 1e7), Stats):
            stats = self.store.fetch(names, latest - timedelta(seconds=seconds), latest)
            self.assertLessEqual(len(stats), seconds / model.step + 1)
            self.assertFalse(any(timestamp(dt) % model.step for dt in stats))
        series, = self.store.series(names[0])
        counts = [model.objects.filter(id=series.id).count() for model in Stats]
        self.assertLess(counts.pop(0), rows)
        self.assertEqual(counts, sorted(counts, reverse=True))
