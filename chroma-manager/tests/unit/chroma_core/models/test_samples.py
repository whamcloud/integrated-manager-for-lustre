import itertools
import time
import contextlib
import operator
from datetime import datetime, timedelta
from django.utils.timezone import utc
from django.test import TestCase
from django.db import connection
from chroma_core.models import Point, Stats

id = 0
now = datetime.now(utc)
points = [Point(now + timedelta(seconds=n * 10), float(n), 1) for n in xrange(100)]


@contextlib.contextmanager
def assertQueries(*prefixes):
    "Assert the correct queries are efficiently executed for a block."
    count = len(connection.queries)
    yield
    for prefix, query in itertools.izip_longest(prefixes, connection.queries[count:]):
        assert prefix and query and query['sql'].startswith(prefix), (prefix, query)
        cursor = connection.cursor()
        cursor.execute('EXPLAIN ' + query['sql'])
        plan = ''.join(row for row, in cursor)
        assert prefix == 'INSERT' or 'Index Scan' in plan, (plan, query)


class TestModels(TestCase):
    "Test Point and Sample interfaces."

    def setUp(self):
        Stats.delete(id)
        connection.use_debug_cursor = True
        connection.cursor().execute('SET enable_seqscan = off')

    def tearDown(self):
        connection.cursor().execute('SET enable_seqscan = on')
        connection.use_debug_cursor = False
        Stats.delete(id)

    def test_point(self):
        self.assertEqual(Point(now, 0.0, 0).mean, 0)
        point = points[0]
        self.assertEqual(point, (point.dt, point.sum, point.len))
        self.assertEqual(point.mean, 0.0)
        self.assertLess(point.timestamp, time.time())
        point = points[0] + points[1]
        self.assertEqual(point, (points[0].dt, 1.0, 2))
        point = points[1] - points[0]
        self.assertEqual(point, (points[1].dt, 1.0, 10))
        self.assertEqual(point.mean, 0.1)

    def test_sample(self):
        model = Stats[0]
        with assertQueries('SELECT', 'SELECT', 'SELECT'):
            point = model.latest(id)
            self.assertEqual(point, model.latest(id))
            start = model.start(id)
        self.assertEqual(point.timestamp, 0)
        self.assertGreater(point.dt - start, timedelta(days=1))
        with assertQueries('INSERT', 'SELECT'):
            model.insert({id: points[:3]})
            point = model.latest(id)
            model.cache.clear()
            self.assertEqual(point, model.latest(id))
        self.assertEqual(point, points[2])
        floor = model.floor(point.dt)
        self.assertLessEqual(floor, point.dt)
        self.assertFalse(floor.microsecond)
        with assertQueries('SELECT', 'DELETE', 'SELECT'):
            model.expire([id])
            self.assertListEqual(list(model.select(id)), points[:3])
        self.assertEqual(len(list(model.reduce(points[:3]))), 3)
        self.assertLess(len(list(Stats[1].reduce(points[:3]))), 3)
        with assertQueries('DELETE'):
            model.delete(id=id)
        self.assertListEqual(list(model.select(id)), [])
        self.assertTrue(Stats[-1].start(id))

    def test_stats(self):
        outdated = Stats.insert((id, point.dt, point.sum) for point in points)
        self.assertEqual(outdated, [])
        with assertQueries():
            point = Stats.latest(id)
        sample = id, point.dt, point.sum
        self.assertEqual(Stats.insert([sample]), [sample])
        self.assertEqual(point.timestamp % 10, 0)
        self.assertGreater(point, points[-2])
        self.assertLessEqual(point, points[-1])
        count = len(points) + 1
        for offset in {'hours': 1}, {'days': 10}, {'days': 100}, {'days': 10000}:
            timestamps = map(operator.attrgetter('timestamp'), Stats.select(id, point.dt - timedelta(**offset), point.dt))
            self.assertLess(len(timestamps), count)
            count = len(timestamps)
            steps = set(y - x for x, y in zip(timestamps, timestamps[1:]))
            self.assertLessEqual(len(steps), 1)
        timestamps = map(operator.attrgetter('timestamp'), Stats.select(id, point.dt - timedelta(hours=1), point.dt, maxlen=100))
        self.assertLessEqual(len(timestamps), 100)
        self.assertFalse(any(timestamp % 60 for timestamp in timestamps))
        self.assertTrue(any(timestamp % 300 for timestamp in timestamps))
        for point in Stats.select(id, point.dt - timedelta(hours=1), point.dt, rate=True):
            self.assertEqual(point[1:], (1.0, 10))
        with assertQueries(*['DELETE'] * 5):
            Stats.delete(id)
        for model in Stats:
            self.assertListEqual(list(model.select(id)), [])
