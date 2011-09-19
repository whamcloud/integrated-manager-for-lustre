from django.test import TestCase
from r3d.models import *
import json

# NB: In the fetch tests, we can't simply assert that expected == actual,
# because in python NaN != NaN.  As a stupid hackaround, we dump the
# dicts to json and compare the strings.  Before that, we do some other
# comparisons to make gross errors a bit more apparent.
class SingleDsTutorialTest(TestCase):
    """
    Tests based on the rrdtool basic tutorial.  Single DS, two RRAs.
    """
    def setUp(self):
        self.rrd = Database.objects.create(name="test", start=920804400)
        self.rrd.datasources.add(Counter.objects.create(name="speed",
                                                        heartbeat=600,
                                                        database=self.rrd))
        self.rrd.archives.add(Average.objects.create(xff="0.5",
                                                     cdp_per_row=1,
                                                     rows=24,
                                                     database=self.rrd))
        self.rrd.archives.add(Average.objects.create(xff="0.5",
                                                     cdp_per_row=6,
                                                     rows=10,
                                                     database=self.rrd))

    def update_database(self):
        for upd_str in """
        920804700:12345 920805000:12357 920805300:12363
        920805600:12363 920805900:12363 920806200:12373
        920806500:12383 920806800:12393 920807100:12399
        920807400:12405 920807700:12411 920808000:12415
        920808300:12420 920808600:12422 920808900:12423
        """.split():
            self.rrd.update(upd_str)

    def test_setup_sanity(self):
        """
        Tests that setup works the way we think it does.
        """
        self.assertEqual(self.rrd.name, "test")
        self.assertEqual(self.rrd.start, 920804400)
        self.assertEqual(self.rrd.step, 300)
        self.assertEqual(self.rrd.datasources.count(), 1)
        self.assertEqual(self.rrd.archives.count(), 2)

    def test_database_fetch(self):
        """
        Tests that what we get back from fetch() is correct.
        """
        self.maxDiff = None
        self.update_database()
        self.assertEqual(self.rrd.last_update, 920808900)

        expected = {
            920804700L: {u'speed': float("NaN")},
            920805000L: {u'speed': 0.040000000000000001},
            920805300L: {u'speed': 0.02},
            920805600L: {u'speed': 0.0},
            920805900L: {u'speed': 0.0},
            920806200L: {u'speed': 0.033333333333333298},
            920806500L: {u'speed': 0.033333333333333298},
            920806800L: {u'speed': 0.033333333333333298},
            920807100L: {u'speed': 0.02},
            920807400L: {u'speed': 0.02},
            920807700L: {u'speed': 0.02},
            920808000L: {u'speed': 0.013333333333333299},
            920808300L: {u'speed': 0.016666666666666701},
            920808600L: {u'speed': 0.0066666666666666697},
            920808900L: {u'speed': 0.0033333333333333301},
            920809200L: {u'speed': float("NaN")},
            920809500L: {u'speed': float("NaN")}
        }

        actual = self.rrd.fetch("Average", 920804400, 920809200)
        self.assertEqual(sorted(expected.keys()), sorted(actual.keys()))
        self.assertEqual(sorted([r.keys() for r in expected.values()]),
                         sorted([r.keys() for r in actual.values()]))
        self.assertEqual(json.dumps(expected), json.dumps(actual))

        expected = {
            920800800L: {u'speed': float("NaN")},
            920802600L: {u'speed': float("NaN")},
            920804400L: {u'speed': float("NaN")},
            920806200L: {u'speed': 0.018666666666666699},
            920808000L: {u'speed': 0.0233333333333334},
            920809800L: {u'speed': float("NaN")}
        }

        actual = self.rrd.fetch("Average", 920799000, 920809200)
        self.assertEqual(sorted(expected.keys()), sorted(actual.keys()))
        self.assertEqual(sorted([r.keys() for r in expected.values()]),
                         sorted([r.keys() for r in actual.values()]))
        self.assertEqual(json.dumps(expected), json.dumps(actual))

    def tearDown(self):
        self.rrd.delete()

class MultiDsTutorialTest(TestCase):
    """
    Tests based on the rrdtool basic tutorial.  Two DSes, two RRAs.
    """
    def setUp(self):
        self.rrd = Database.objects.create(name="test", start=920804400)
        self.rrd.datasources.add(Counter.objects.create(name="speed",
                                                        heartbeat=600,
                                                        database=self.rrd))
        self.rrd.datasources.add(Gauge.objects.create(name="kbytes_free",
                                                        heartbeat=600,
                                                        database=self.rrd))
        self.rrd.archives.add(Average.objects.create(xff="0.5",
                                                     cdp_per_row=1,
                                                     rows=24,
                                                     database=self.rrd))
        self.rrd.archives.add(Average.objects.create(xff="0.5",
                                                     cdp_per_row=6,
                                                     rows=10,
                                                     database=self.rrd))

    def update_database(self):
        for upd_str in """
        920804700:12345:1979620 920805000:12357:1979619 920805300:12363:1979618
        920805600:12363:1979617 920805900:12363:1979616 920806200:12373:1979615
        920806500:12383:1979614 920806800:12393:1979613 920807100:12399:1979612
        920807400:12405:1979612 920807700:12411:1979611 920808000:12415:1979608
        920808300:12420:1979570 920808600:12422:1979800 920808900:12423:1979940
        """.split():
            self.rrd.update(upd_str)

    def test_setup_sanity(self):
        """
        Tests that setup works the way we think it does.
        """
        self.assertEqual(self.rrd.name, "test")
        self.assertEqual(self.rrd.start, 920804400)
        self.assertEqual(self.rrd.step, 300)
        self.assertEqual(self.rrd.datasources.count(), 2)
        self.assertEqual(self.rrd.archives.count(), 2)

    def test_database_fetch(self):
        """
        Tests that what we get back from fetch() is correct.
        """
        self.maxDiff = None
        self.update_database()
        self.assertEqual(self.rrd.last_update, 920808900)

        expected = {
            920804700L: {u'speed': float("NaN"), u'kbytes_free': 1979620.0},
            920805000L: {u'speed': 0.040000000000000001, u'kbytes_free': 1979619.0},
            920805300L: {u'speed': 0.02, u'kbytes_free': 1979618.0},
            920805600L: {u'speed': 0.0, u'kbytes_free': 1979617.0},
            920805900L: {u'speed': 0.0, u'kbytes_free': 1979616.0},
            920806200L: {u'speed': 0.033333333333333298, u'kbytes_free': 1979615.0},
            920806500L: {u'speed': 0.033333333333333298, u'kbytes_free': 1979614.0},
            920806800L: {u'speed': 0.033333333333333298, u'kbytes_free': 1979613.0},
            920807100L: {u'speed': 0.02, u'kbytes_free': 1979612.0},
            920807400L: {u'speed': 0.02, u'kbytes_free': 1979612.0},
            920807700L: {u'speed': 0.02, u'kbytes_free': 1979611.0},
            920808000L: {u'speed': 0.013333333333333299, u'kbytes_free': 1979608.0},
            920808300L: {u'speed': 0.016666666666666701, u'kbytes_free': 1979570.0},
            920808600L: {u'speed': 0.0066666666666666697, u'kbytes_free': 1979800.0},
            920808900L: {u'speed': 0.0033333333333333301, u'kbytes_free': 1979940.0},
            920809200L: {u'speed': float("NaN"), u'kbytes_free': float("NaN")},
            920809500L: {u'speed': float("NaN"), u'kbytes_free': float("NaN")}
        }

        actual = self.rrd.fetch("Average", 920804400, 920809200)
        self.assertEqual(sorted(expected.keys()), sorted(actual.keys()))
        self.assertEqual(sorted([r.keys() for r in expected.values()]),
                         sorted([r.keys() for r in actual.values()]))
        self.assertEqual(json.dumps(expected), json.dumps(actual))

        expected = {
            920800800L: {u'speed': float("NaN"), u'kbytes_free': float("NaN")},
            920802600L: {u'speed': float("NaN"), u'kbytes_free': float("NaN")},
            920804400L: {u'speed': float("NaN"), u'kbytes_free': float("NaN")},
            920806200L: {u'speed': 0.018666666666666699, u'kbytes_free': 1979617.5},
            920808000L: {u'speed': 0.0233333333333334, u'kbytes_free': 1979611.66666667},
            920809800L: {u'speed': float("NaN"), u'kbytes_free': float("NaN")}
        }

        actual = self.rrd.fetch("Average", 920799000, 920809200)
        self.assertEqual(sorted(expected.keys()), sorted(actual.keys()))
        self.assertEqual(sorted([r.keys() for r in expected.values()]),
                         sorted([r.keys() for r in actual.values()]))
        self.assertEqual(json.dumps(expected), json.dumps(actual))

    def tearDown(self):
        self.rrd.delete()

class LongerMultiDSOverlaps(TestCase):
    """
    Start with two DSes, but feed one DS values for a while, and the other
    NaNs.  Then switch it.  The larger input set helps to provoke
    consolidation bugs.
    """
    def setUp(self):
        self.rrd = Database.objects.create(name="test", start=920804400)
        self.rrd.datasources.add(Counter.objects.create(name="speed",
                                                        heartbeat=600,
                                                        database=self.rrd))
        self.rrd.datasources.add(Gauge.objects.create(name="kbytes_free",
                                                        heartbeat=600,
                                                        database=self.rrd))
        self.rrd.archives.add(Average.objects.create(xff=0.5,
                                                     cdp_per_row=1,
                                                     rows=24,
                                                     database=self.rrd))
        self.rrd.archives.add(Average.objects.create(xff=0.5,
                                                     cdp_per_row=6,
                                                     rows=10,
                                                     database=self.rrd))

        for upd_str in """
        920804700:12345:U 920805000:12357:U 920805300:12363:U
        920805600:12363:U 920805900:12363:U 920806200:12373:U
        920806500:12383:U 920806800:12393:U 920807100:12399:U
        920807400:12405:U 920807700:12411:U 920808000:12415:U
        920808300:12420:U 920808600:12422:U 920808900:12423:U
        920809200:U:1979620 920809500:U:1979619 920809800:U:1979618
        920810100:U:1979617 920810400:U:1979616 920810700:U:1979615
        920811000:U:1979614 920811300:U:1979613 920811600:U:1979612
        920811900:U:1979611 920812200:U:1979610 920812500:U:1979609
        920812800:U:1979608 920813100:U:1979607 920813400:U:1979640
        """.split():
            self.rrd.update(upd_str)

    def test_database_fetch(self):
        """
        Tests that what we get back from fetch() is correct.
        """
        self.maxDiff = None
        self.assertEqual(self.rrd.last_update, 920813400)

        expected = {
            920806200L: {u'speed': 0.018666666666666699, u'kbytes_free': float("NaN")},
            920808000L: {u'speed': 0.0233333333333334, u'kbytes_free': float("NaN")},
            920809800L: {u'speed': 0.0088888888888888993, u'kbytes_free': 1979619.0},
            920811600L: {u'speed': float("NaN"), u'kbytes_free': 1979614.5},
            920813400L: {u'speed': float("NaN"), u'kbytes_free': 1979614.16666667},
            920815200L: {u'speed': float("NaN"), u'kbytes_free': float("NaN")}
        }

        actual = self.rrd.fetch("Average", 920804400, 920813400)
        #print json.dumps(actual, sort_keys=True, indent=2)
        self.assertEqual(sorted(expected.keys()), sorted(actual.keys()))
        self.assertEqual(sorted([r.keys() for r in expected.values()]),
                         sorted([r.keys() for r in actual.values()]))
        self.assertEqual(json.dumps(expected), json.dumps(actual))

    def tearDown(self):
        self.rrd.delete()

class PostCreateNewDs(TestCase):
    """
    Start with a single DS, update a bunch of values, then add another DS
    and verify that fetched values match expectations.  This is something
    rrdtool can't easily handle.  This is the same input dataset as in
    LongerMultiDSOverlaps, so the expected results should be identical.
    """
    def setUp(self):
        self.rrd = Database.objects.create(name="test", start=920804400)
        self.rrd.datasources.add(Counter.objects.create(name="speed",
                                                        heartbeat=600,
                                                        database=self.rrd))
        self.rrd.archives.add(Average.objects.create(xff=0.5,
                                                     cdp_per_row=1,
                                                     rows=24,
                                                     database=self.rrd))
        self.rrd.archives.add(Average.objects.create(xff=0.5,
                                                     cdp_per_row=6,
                                                     rows=10,
                                                     database=self.rrd))

        for upd_str in """
        920804700:12345 920805000:12357 920805300:12363
        920805600:12363 920805900:12363 920806200:12373
        920806500:12383 920806800:12393 920807100:12399
        920807400:12405 920807700:12411 920808000:12415
        920808300:12420 920808600:12422 920808900:12423
        """.split():
            self.rrd.update(upd_str)

        self.rrd.datasources.add(Gauge.objects.create(name="kbytes_free",
                                                        heartbeat=600,
                                                        database=self.rrd))

        for upd_str in """
        920809200:U:1979620 920809500:U:1979619 920809800:U:1979618
        920810100:U:1979617 920810400:U:1979616 920810700:U:1979615
        920811000:U:1979614 920811300:U:1979613 920811600:U:1979612
        920811900:U:1979611 920812200:U:1979610 920812500:U:1979609
        920812800:U:1979608 920813100:U:1979607 920813400:U:1979640
        """.split():
            self.rrd.update(upd_str)

    def test_database_fetch(self):
        """
        Tests that what we get back from fetch() is correct.
        """
        self.maxDiff = None
        self.assertEqual(self.rrd.last_update, 920813400)

        expected = {
            920806200L: {u'speed': 0.018666666666666699, u'kbytes_free': float("NaN")},
            920808000L: {u'speed': 0.0233333333333334, u'kbytes_free': float("NaN")},
            920809800L: {u'speed': 0.0088888888888888993, u'kbytes_free': 1979619.0},
            920811600L: {u'speed': float("NaN"), u'kbytes_free': 1979614.5},
            920813400L: {u'speed': float("NaN"), u'kbytes_free': 1979614.16666667},
            920815200L: {u'speed': float("NaN"), u'kbytes_free': float("NaN")}
        }

        actual = self.rrd.fetch("Average", 920804400, 920813400)
        #print json.dumps(actual, sort_keys=True, indent=2)
        self.assertEqual(sorted(expected.keys()), sorted(actual.keys()))
        self.assertEqual(sorted([r.keys() for r in expected.values()]),
                         sorted([r.keys() for r in actual.values()]))
        self.assertEqual(json.dumps(expected), json.dumps(actual))

    def tearDown(self):
        self.rrd.delete()
