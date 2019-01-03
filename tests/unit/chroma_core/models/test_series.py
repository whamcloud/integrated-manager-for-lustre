import random
from datetime import datetime, timedelta

from django.utils.timezone import utc
from django.contrib.auth.models import User

from tests.unit.lib.iml_unit_test_case import IMLUnitTestCase
from tests.utils import patch
from chroma_core.lib import metrics
from chroma_core.models.stats import Series, Stats, timestamp


fields = ("size", "Gauge", 0, 1000), ("bandwith", "Counter", 0, 100), ("speed", "Derive", -100, 100)
epoch = datetime.fromtimestamp(0, utc)


def gen_series(sample, rows):
    "Generate sample timestamps and randomized data."
    for index in xrange(rows):
        yield (index * sample), dict(
            (field[0], {"type": field[1], "value": random.randint(*field[2:])}) for field in fields
        )


class TestSeries(IMLUnitTestCase):
    "Test series updates and fetches at the MetricStore layer"

    def setUp(self):
        super(TestSeries, self).setUp()

        self.obj = User.objects.create(username="test", email="test@test.test")
        self.store = metrics.MetricStore(self.obj)

    def tearDown(self):
        self.store.clear()
        self.obj.delete()

    def test_integrity(self):
        field, type = fields[0][:2]
        series = Series.get(self.obj, field, type)
        self.assertIs(series, Series.get(self.obj, field))
        Series.cache.clear()
        with patch(Series.cache, SIZE=0):
            self.assertEqual(series, Series.get(self.obj, field))
        self.assertFalse(Series.cache)

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
        stats = self.store.fetch(names[:1], epoch, epoch + timedelta(seconds=20))
        self.assertEqual(len(stats), 2)
        dt = min(stats)
        data = stats[dt]
        self.assertEqual(dt, epoch)
        for name, type, start, stop in fields:
            if type == "Gauge":
                self.assertGreaterEqual(data[name], start)
                self.assertLessEqual(data[name], stop)
            else:
                self.assertNotIn(name, data)
        stats = self.store.fetch(names, epoch, epoch + timedelta(seconds=20))
        self.assertEqual(len(stats), 1)
        dt = min(stats)
        data = stats[dt]
        self.assertEqual(timestamp(dt), 10)
        for name, type, start, stop in fields:
            delta = (stop - start) / 10.0
            if type == "Gauge":
                self.assertGreaterEqual(data[name], start)
                self.assertLessEqual(data[name], stop)
            elif type == "Counter":
                self.assertGreaterEqual(data[name], 0.0)
                self.assertLessEqual(data[name], delta)
            else:
                self.assertGreaterEqual(data[name], -delta)
                self.assertLessEqual(data[name], delta)
        # verify update queries would aggregate to the same result
        stats = self.store.fetch(names, epoch, epoch + timedelta(seconds=40))
        for delta in (0, 10, 20):
            start = epoch + timedelta(seconds=delta)
            (dt, data), = self.store.fetch(names, start, start + timedelta(seconds=25)).items()
            self.assertEqual(stats.pop(dt), data)
        self.assertEqual(stats, {})

    def test_slow(self):
        "Large data set with long intervals."
        rows = 1100
        for data in zip(*[gen_series(100, rows)] * 10):
            Stats.insert(self.store.serialize(dict(data)))
        names = [field[0] for field in fields]
        latest, data = self.store.fetch_last(names)
        for seconds, model in zip((1e4, 5e4, 1e5, 1e6, 1e7), Stats):
            stats = self.store.fetch(names, latest - timedelta(seconds=seconds), latest, max_points=1000)
            self.assertLessEqual(len(stats), seconds / model.step + 1)
            self.assertFalse(any(timestamp(dt) % model.step for dt in stats))
        series = Series.filter(self.obj)[0]
        counts = [model.objects.filter(id=series.id).count() for model in Stats]
        self.assertLess(counts.pop(0), rows)
        self.assertEqual(counts, sorted(counts, reverse=True))
