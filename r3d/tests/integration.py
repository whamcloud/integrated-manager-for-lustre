## Copyright 2011 Whamcloud, Inc.
## Authors: Michael MacDonald <mjmac@whamcloud.com>

from django.test import TestCase
import r3d.models
from r3d.models import *
import json

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

        expected = (
            (920804700L, {u'speed': None}),
            (920805000L, {u'speed': 0.040000000000000001}),
            (920805300L, {u'speed': 0.02}),
            (920805600L, {u'speed': 0.0}),
            (920805900L, {u'speed': 0.0}),
            (920806200L, {u'speed': 0.033333333333333298}),
            (920806500L, {u'speed': 0.033333333333333298}),
            (920806800L, {u'speed': 0.033333333333333298}),
            (920807100L, {u'speed': 0.02}),
            (920807400L, {u'speed': 0.02}),
            (920807700L, {u'speed': 0.02}),
            (920808000L, {u'speed': 0.013333333333333299}),
            (920808300L, {u'speed': 0.016666666666666701}),
            (920808600L, {u'speed': 0.0066666666666666697}),
            (920808900L, {u'speed': 0.0033333333333333301}),
            (920809200L, {u'speed': None}),
            (920809500L, {u'speed': None})
        )

        actual = self.rrd.fetch("Average", 920804400, 920809200)
        self.assertEqual(expected, actual)

        expected = (
            (920800800L, {u'speed': None}),
            (920802600L, {u'speed': None}),
            (920804400L, {u'speed': None}),
            (920806200L, {u'speed': 0.018666666666666699}),
            (920808000L, {u'speed': 0.0233333333333334}),
            (920809800L, {u'speed': None})
        )

        actual = self.rrd.fetch("Average", 920799000, 920809200)
        self.assertEqual(expected, actual)

        expected = (
            920808900L, {u'speed': 12423}
        )

        actual = self.rrd.fetch_last()
        self.assertEqual(expected, actual)

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

        expected = (
            (920804700L, {u'speed': None, u'kbytes_free': 1979620.0}),
            (920805000L, {u'speed': 0.040000000000000001, u'kbytes_free': 1979619.0}),
            (920805300L, {u'speed': 0.02, u'kbytes_free': 1979618.0}),
            (920805600L, {u'speed': 0.0, u'kbytes_free': 1979617.0}),
            (920805900L, {u'speed': 0.0, u'kbytes_free': 1979616.0}),
            (920806200L, {u'speed': 0.033333333333333298, u'kbytes_free': 1979615.0}),
            (920806500L, {u'speed': 0.033333333333333298, u'kbytes_free': 1979614.0}),
            (920806800L, {u'speed': 0.033333333333333298, u'kbytes_free': 1979613.0}),
            (920807100L, {u'speed': 0.02, u'kbytes_free': 1979612.0}),
            (920807400L, {u'speed': 0.02, u'kbytes_free': 1979612.0}),
            (920807700L, {u'speed': 0.02, u'kbytes_free': 1979611.0}),
            (920808000L, {u'speed': 0.013333333333333299, u'kbytes_free': 1979608.0}),
            (920808300L, {u'speed': 0.016666666666666701, u'kbytes_free': 1979570.0}),
            (920808600L, {u'speed': 0.0066666666666666697, u'kbytes_free': 1979800.0}),
            (920808900L, {u'speed': 0.0033333333333333301, u'kbytes_free': 1979940.0}),
            (920809200L, {u'speed': None, u'kbytes_free': None}),
            (920809500L, {u'speed': None, u'kbytes_free': None})
        )

        actual = self.rrd.fetch("Average", 920804400, 920809200)
        self.assertEqual(expected, actual)

        expected = (
            (920800800L, {u'speed': None, u'kbytes_free': None}),
            (920802600L, {u'speed': None, u'kbytes_free': None}),
            (920804400L, {u'speed': None, u'kbytes_free': None}),
            (920806200L, {u'speed': 0.018666666666666699, u'kbytes_free': 1979617.5}),
            (920808000L, {u'speed': 0.0233333333333334, u'kbytes_free': 1979611.66666667}),
            (920809800L, {u'speed': None, u'kbytes_free': None})
        )

        actual = self.rrd.fetch("Average", 920799000, 920809200)
        self.assertEqual(expected, actual)

        expected = (
            920808900L, {u'speed': 12423, u'kbytes_free': 1979940}
        )

        actual = self.rrd.fetch_last()
        self.assertEqual(expected, actual)

        expected = (
            920808900L, {u'speed': 12423}
        )

        actual = self.rrd.fetch_last(['speed'])
        self.assertEqual(expected, actual)

        expected = (
            (920800800L, {u'kbytes_free': None}),
            (920802600L, {u'kbytes_free': None}),
            (920804400L, {u'kbytes_free': None}),
            (920806200L, {u'kbytes_free': 1979617.5}),
            (920808000L, {u'kbytes_free': 1979611.66666667}),
            (920809800L, {u'kbytes_free': None})
        )

        actual = self.rrd.fetch("Average",
                                start_time=920799000,
                                end_time=920809200,
                                fetch_metrics=["kbytes_free"])
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

        expected = (
            (920806200L, {u'speed': 0.018666666666666699, u'kbytes_free': None}),
            (920808000L, {u'speed': 0.0233333333333334, u'kbytes_free': None}),
            (920809800L, {u'speed': 0.0088888888888888993, u'kbytes_free': 1979619.0}),
            (920811600L, {u'speed': None, u'kbytes_free': 1979614.5}),
            (920813400L, {u'speed': None, u'kbytes_free': 1979614.16666667}),
            (920815200L, {u'speed': None, u'kbytes_free': None})
        )

        actual = self.rrd.fetch("Average", 920804400, 920813400)
        self.assertEqual(expected, actual)

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

        expected = (
            (920806200L, {u'speed': 0.018666666666666699, u'kbytes_free': None}),
            (920808000L, {u'speed': 0.0233333333333334, u'kbytes_free': None}),
            (920809800L, {u'speed': 0.0088888888888888993, u'kbytes_free': 1979619.0}),
            (920811600L, {u'speed': None, u'kbytes_free': 1979614.5}),
            (920813400L, {u'speed': None, u'kbytes_free': 1979614.16666667}),
            (920815200L, {u'speed': None, u'kbytes_free': None})
        )

        actual = self.rrd.fetch("Average", 920804400, 920813400)
        self.assertEqual(expected, actual)

    def tearDown(self):
        self.rrd.delete()

class SingleDsUpdateDictTest(TestCase):
    """
    Same as the first SingleDS test, but inputs come as a dict instead of
    string.
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
        one = {
            920804700: {'speed': 12345},
            920805000: {'speed': 12357},
            920805300: {'speed': 12363},
            920805600: {'speed': 12363},
            920805900: {'speed': 12363},
            920806200: {'speed': 12373},
            920806500: {'speed': 12383},
            920806800: {'speed': 12393},
            920807100: {'speed': 12399},
            920807400: {'speed': 12405},
            920807700: {'speed': 12411},
            920808000: {'speed': 12415}
        }
        two = {920808300: {'speed': 12420}}
        three = {920808600: {'speed': 12422}}
        four = {920808900: {'speed': 12423}}
        self.rrd.update(one)
        self.rrd.update(two)
        self.rrd.update(three)
        self.rrd.update(four)

    def test_database_fetch(self):
        """
        Tests that what we get back from fetch() is correct.
        """
        self.maxDiff = None
        self.update_database()
        self.assertEqual(self.rrd.last_update, 920808900)

        expected = (
            (920804700L, {u'speed': None}),
            (920805000L, {u'speed': 0.040000000000000001}),
            (920805300L, {u'speed': 0.02}),
            (920805600L, {u'speed': 0.0}),
            (920805900L, {u'speed': 0.0}),
            (920806200L, {u'speed': 0.033333333333333298}),
            (920806500L, {u'speed': 0.033333333333333298}),
            (920806800L, {u'speed': 0.033333333333333298}),
            (920807100L, {u'speed': 0.02}),
            (920807400L, {u'speed': 0.02}),
            (920807700L, {u'speed': 0.02}),
            (920808000L, {u'speed': 0.013333333333333299}),
            (920808300L, {u'speed': 0.016666666666666701}),
            (920808600L, {u'speed': 0.0066666666666666697}),
            (920808900L, {u'speed': 0.0033333333333333301}),
            (920809200L, {u'speed': None}),
            (920809500L, {u'speed': None})
        )

        actual = self.rrd.fetch("Average", 920804400, 920809200)
        self.assertEqual(expected, actual)

        expected = (
            (920800800L, {u'speed': None}),
            (920802600L, {u'speed': None}),
            (920804400L, {u'speed': None}),
            (920806200L, {u'speed': 0.018666666666666699}),
            (920808000L, {u'speed': 0.0233333333333333}),
            (920809800L, {u'speed': None})
        )

        actual = self.rrd.fetch("Average", 920799000, 920809200)
        self.assertEqual(expected, actual)

    def tearDown(self):
        self.rrd.delete()

class PostCreateNewDsUpdateDict(TestCase):
    """
    As with the previous PostCreate test case, we'll:
    Start with a single DS, update a bunch of values, then add another DS
    and verify that fetched values match expectations.  The difference is
    that the new DS comes in via the update dict, and this code tests
    our missing_ds_block callback handler.
    This is the same input dataset as in
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

        def missing_ds_fn(rrd, ds_name, ds_value):
            metric_map = {
                'kbytes_free': Gauge
            }
            try:
                ds_cls = metric_map[ds_name]
            except KeyError:
                ds_cls = Counter

            ds = ds_cls.objects.create(name=ds_name,
                                       heartbeat=600,
                                       database=rrd)
            rrd.datasources.add(ds)

        updates = {
            920809200: {'kbytes_free': 1979620},
            920809500: {'kbytes_free': 1979619},
            920809800: {'kbytes_free': 1979618},
        }

        self.rrd.update(updates, missing_ds_fn)

        for upd_str in """
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

        expected = (
            (920806200L, {u'speed': 0.018666666666666699, u'kbytes_free': None}),
            (920808000L, {u'speed': 0.0233333333333334, u'kbytes_free': None}),
            (920809800L, {u'speed': 0.0088888888888888993, u'kbytes_free': 1979619.0}),
            (920811600L, {u'speed': None, u'kbytes_free': 1979614.5}),
            (920813400L, {u'speed': None, u'kbytes_free': 1979614.16666667}),
            (920815200L, {u'speed': None, u'kbytes_free': None})
        )

        actual = self.rrd.fetch("Average", 920804400, 920813400)
        self.assertEqual(expected, actual)

    def tearDown(self):
        self.rrd.delete()

class PostCreateNewDsUpdateDictWithOpts(TestCase):
    """
    Same thing, but this time supplying the DS options via the update
    dict and using them in missing_ds_fn.
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

        updates = {
            920809200: {'kbytes_free': {'value': 1979620, 'type': 'Gauge', 'heartbeat': 600}},
            920809500: {'kbytes_free': {'value': 1979619, 'type': 'Gauge', 'heartbeat': 600}},
            920809800: {'kbytes_free': {'value': 1979618, 'type': 'Gauge', 'heartbeat': 600}},
        }

        def missing_ds_fn(rrd, ds_name, ds_value):
            ds_cls = getattr(r3d.models, ds_value['type'].capitalize())

            ds = ds_cls.objects.create(name=ds_name,
                                       heartbeat=600,
                                       database=rrd)
            rrd.datasources.add(ds)

        self.rrd.update(updates, missing_ds_fn)

        for upd_str in """
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

        expected = (
            (920806200L, {u'speed': 0.018666666666666699, u'kbytes_free': None}),
            (920808000L, {u'speed': 0.0233333333333334, u'kbytes_free': None}),
            (920809800L, {u'speed': 0.0088888888888888993, u'kbytes_free': 1979619.0}),
            (920811600L, {u'speed': None, u'kbytes_free': 1979614.5}),
            (920813400L, {u'speed': None, u'kbytes_free': 1979614.16666667}),
            (920815200L, {u'speed': None, u'kbytes_free': None})
        )

        actual = self.rrd.fetch("Average", 920804400, 920813400)
        self.assertEqual(expected, actual)

    def tearDown(self):
        self.rrd.delete()

class BugHyd330(TestCase):
    """HYD-330 Stats go haywire when they aren't sent in fast enough."""
    def setUp(self):
        audit_freq = 1
        self.rrd = Database.objects.create(name="hyd330",
                                           start=1318119547,
                                           step=audit_freq)
        self.rrd.datasources.add(Counter.objects.create(name="ds_counter",
                                                      heartbeat=audit_freq * 10,
                                                       database=self.rrd))
        self.rrd.datasources.add(Gauge.objects.create(name="ds_gauge",
                                                      heartbeat=audit_freq * 10,
                                                      database=self.rrd))
        # High resolution, stores an hour's worth of 1s samples.
        self.rrd.archives.add(Average.objects.create(xff="0.5",
                                                     cdp_per_row=1,
                                                     rows=3600,
                                                     database=self.rrd))

    def update_database(self):
        import os, re

        datafile = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "data", "hyd330.txt"))
        for line in datafile.readlines():
            if re.match("^#", line):
                continue
            self.rrd.update(line[:-1])

    def test_database_fetch(self):
        """
        Tests that what we get back from fetch() is correct.
        """
        self.maxDiff = None
        self.update_database()

        expected = (
            (1318119573L, {u'ds_counter': 15.00, u'ds_gauge': 666372426631.00}),
            (1318119574L, {u'ds_counter': 15.00, u'ds_gauge': 666372426631.00}),
            (1318119575L, {u'ds_counter': 15.00, u'ds_gauge': 666372426631.00}),
            (1318119576L, {u'ds_counter': 15.00, u'ds_gauge': 666372426631.00}),
            (1318119577L, {u'ds_counter': 75.00, u'ds_gauge': 836543304155.00}),
            (1318119578L, {u'ds_counter': 50.00, u'ds_gauge': 719193055283.00}),
            (1318119579L, {u'ds_counter': 114.00, u'ds_gauge': 866324622517.00}),
            (1318119580L, {u'ds_counter': 24.00, u'ds_gauge': 126215566607.00}),
            (1318119581L, {u'ds_counter': 93.00, u'ds_gauge': 931746070743.00}),
            (1318119582L, {u'ds_counter': 70.00, u'ds_gauge': 788226844642.00}),
            (1318119583L, {u'ds_counter': 70.00, u'ds_gauge': 788226844642.00}),
            (1318119584L, {u'ds_counter': 70.00, u'ds_gauge': 788226844642.00}),
            (1318119585L, {u'ds_counter': 70.00, u'ds_gauge': 788226844642.00}),
            (1318119586L, {u'ds_counter': 232.00, u'ds_gauge': 5778155993.00}),
            (1318119587L, {u'ds_counter': 459.00, u'ds_gauge': 488524292802.00}),
            (1318119588L, {u'ds_counter': 86.00, u'ds_gauge': 157541304916.00}),
            (1318119589L, {u'ds_counter': 28.00, u'ds_gauge': 423229610200.00}),
            (1318119590L, {u'ds_counter': 102.00, u'ds_gauge': 767578959806.00}),
            (1318119591L, {u'ds_counter': 107.00, u'ds_gauge': 112959752889.00}),
            (1318119592L, {u'ds_counter': 616.00, u'ds_gauge': 434864698130.00}),
            (1318119593L, {u'ds_counter': 21.00, u'ds_gauge': 962152427501.00}),
            (1318119594L, {u'ds_counter': None, u'ds_gauge': None}),
            (1318119595L, {u'ds_counter': None, u'ds_gauge': None}),
            (1318119596L, {u'ds_counter': None, u'ds_gauge': None}),
            (1318119597L, {u'ds_counter': None, u'ds_gauge': None}),
            (1318119598L, {u'ds_counter': None, u'ds_gauge': None}),
        )

        actual = self.rrd.fetch("Average", 1318119572, 1318119597)
        self.assertEqual(expected, actual)

    def tearDown(self):
        self.rrd.delete()

