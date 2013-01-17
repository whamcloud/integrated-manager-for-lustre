#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import time

from django.test import TestCase
from r3d.models import Database, Counter, Gauge, Average


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
        import os
        import re

        datafile = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "sample_data", "hyd330.txt"))
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
        )

        actual = self.rrd.fetch("Average", 1318119572, 1318119597)
        self.assertEqual(expected, actual)

    def tearDown(self):
        self.rrd.delete()


class BugHyd352(TestCase):
    """
    HYD-352 Metrics stop working if two creations clash

    Metrics code tries to .get Database objects by content type + object id.
    However, creations aren't serialized: if someone visits stats page in GUI
    at same time as first audit is happening, you get two runs of
    _create_r3d, and two Database objects. When that happens, all the
    .get calls throw exceptions and stats collection and reporting breaks.
    No need for catching the exception if you put a uniqueness constraint
    in the model (patch below).
    """
    def test_double_create_raises_integrity_error(self):
        from django.contrib.auth.models import User
        from django.contrib.contenttypes.models import ContentType
        from django.db import IntegrityError

        audit_freq = 1

        user = User.objects.create(username='test', email='test@test.test')
        ct = ContentType.objects.get_for_model(user)

        self.rrd = Database.objects.create(name="hyd352",
                                           start=1318119547,
                                           step=audit_freq,
                                           content_type=ct,
                                           object_id=user.id)

        self.assertRaises(IntegrityError,
                          Database.objects.create,
                          name="hyd352",
                          start=1318119547,
                          step=audit_freq,
                          content_type=ct,
                          object_id=user.id)

    def tearDown(self):
        # Clean up after IntegrityError
        from django.db import connection
        connection._rollback()
        self.rrd.delete()


class BugHyd371(TestCase):
    """HYD-371 omit trailing Nones when fetching most recent data"""
    def setUp(self):
        self.audit_freq = 3600
        self.start_time = long(time.time()) - (self.audit_freq * 6)
        self.rrd = Database.objects.create(name="hyd371",
                                           start=self.start_time - (self.audit_freq),
                                           step=self.audit_freq)
        self.rrd.datasources.add(Gauge.objects.create(name="ds_gauge",
                                                      heartbeat=self.audit_freq * 2,
                                                      database=self.rrd))
        self.rrd.archives.add(Average.objects.create(xff="0.5",
                                                     cdp_per_row=1,
                                                     rows=24,
                                                     database=self.rrd))

    def update_database(self):
        updates = {}
        for i in range(self.start_time,
                       self.start_time + (self.audit_freq * 5),
                       self.audit_freq):
            updates[i] = {'ds_gauge': (i - self.start_time) / self.audit_freq}

        self.rrd.update(updates)

    def test_database_fetch(self):
        """
        Returned rowset should not include rows newer than the supplied
        end time.
        """
        self.maxDiff = None
        self.update_database()

        test_row_count = 3
        start_slot = self.start_time - (self.start_time % self.audit_freq)
        end_slot = start_slot + (self.audit_freq * test_row_count)

        expected_rows = []
        for row_time in range(start_slot + self.audit_freq,
                              end_slot + self.audit_freq, self.audit_freq):
            expected_rows.append(long(row_time))

        end_time = self.start_time + (self.audit_freq * test_row_count)
        actual = self.rrd.fetch("Average", self.start_time, end_time)
        # In this test, we don't care about the values returned, just the
        # set of rows.  We shouldn't get rows newer than end_time because
        # they'll necessarily be full of NaNs if end_time is now().
        self.assertSequenceEqual(expected_rows, [r[0] for r in actual])

    def tearDown(self):
        self.rrd.delete()


class BugHyd985(TestCase):
    """HYD-985 NaNs should never get past fetch()/fetch_last()"""
    def setUp(self):
        self.audit_freq = 10
        self.start_time = long(time.time()) - (self.audit_freq * 5)
        self.rrd = Database.objects.create(name="hyd985",
                                           start=self.start_time - (self.audit_freq),
                                           step=self.audit_freq)
        self.rrd.datasources.add(Gauge.objects.create(name="ds_gauge",
                                                      heartbeat=self.audit_freq * 2,
                                                      database=self.rrd))
        self.rrd.archives.add(Average.objects.create(xff="0.5",
                                                     cdp_per_row=1,
                                                     rows=24,
                                                     database=self.rrd))

    def update_database(self):
        updates = {}
        for i in range(self.start_time,
                       self.start_time + (self.audit_freq * 5),
                       self.audit_freq):
            updates[i] = {'ds_gauge': float("nan")}

        self.rrd.update(updates)

    def test_database_fetch(self):
        """
        fetch_last() should never return NaNs
        """
        self.maxDiff = None
        self.update_database()

        last_tuple = self.rrd.fetch_last()
        self.assertEqual({u'ds_gauge': None}, last_tuple[1])

    def tearDown(self):
        self.rrd.delete()


class BugHyd997(TestCase):
    """HYD-997 Add toggle to R3D for empty gaps"""
    def setUp(self):
        self.audit_freq = 10
        self.sample_count = 360
        self.start_time = long(time.time()) - (self.audit_freq *
                                               self.sample_count)
        self.rrd = Database.objects.create(name="hyd917",
                                           start=self.start_time - (self.audit_freq),
                                           step=self.audit_freq)
        self.rrd.datasources.add(Counter.objects.create(name="ds_counter",
                                                      heartbeat=self.audit_freq * 2,
                                                      database=self.rrd))
        self.rrd.archives.add(Average.objects.create(xff="0.5",
                                                     cdp_per_row=6,
                                                     rows=60,
                                                     database=self.rrd))

    def test_11_minutes_of_none(self):
        """
        fetch() for the past 20 minutes should contain 11 minutes of None
        """
        self.maxDiff = None
        # Test plan:
        # 1. Set up a Counter with a 60mins-of-1min-samples RRA
        # 2. Update normally until 12 min ago
        # 3. Skip over 12 min of updates
        # 4. Add a new update
        # 5. Fetch back 20min, verify that the 11-12min gap is full of None,
        #    not interpolated stats
        updates = {}
        update_value = 0
        until_12_ago = self.start_time + (self.audit_freq * (self.sample_count - 72))
        nowish = self.start_time + (self.audit_freq * self.sample_count)
        for i in range(self.start_time,
                       until_12_ago,
                       self.audit_freq):
            update_value += i % self.start_time
            updates[i] = {'ds_counter': update_value}

        import r3d
        r3d.EMPTY_GAPS = True
        self.rrd.update(updates)

        updates = {}
        updates[nowish] = {'ds_counter': update_value + 3000}

        self.rrd.update(updates)
        r3d.EMPTY_GAPS = False

        about_20_ago = self.start_time + (self.audit_freq *
                                          (self.sample_count - 120))
        last_20 = self.rrd.fetch('Average', start_time=about_20_ago)

        # Depending on where the update/consolidation boundaries fall, it could be 11
        # or 12 rows of None.  It should never be fewer than 11, though.
        empty_rows = last_20[-12:-1]
        self.assertSequenceEqual([None for i in range(11)],
                                 [r[1]['ds_counter'] for r in empty_rows])

    def tearDown(self):
        self.rrd.delete()


class BugUnwrappedRra(TestCase):
    """RRAs which haven't wrapped around yet return strange results"""
    def setUp(self):
        self.audit_freq = 10
        self.sample_count = 110
        self.start_time = 1336849200L
        self.rrd = Database.objects.create(name="unwrapped_rra",
                                           start=self.start_time - (self.audit_freq),
                                           step=self.audit_freq)
        self.rrd.datasources.add(Counter.objects.create(name="ds_counter",
                                                      heartbeat=self.audit_freq * 2,
                                                      database=self.rrd))
        self.rrd.archives.add(Average.objects.create(xff="0.5",
                                                     cdp_per_row=1,
                                                     rows=18,
                                                     database=self.rrd))
        self.rrd.archives.add(Average.objects.create(xff="0.5",
                                                     cdp_per_row=10,
                                                     rows=6,
                                                     database=self.rrd))

    def test_unwrapped_rras_return_sane_results(self):
        update_value = 0
        nowish = self.start_time + (self.audit_freq * self.sample_count)
        for i in range(self.start_time, nowish, self.audit_freq):
            update_value += i % self.start_time
            self.rrd.update({i: {'ds_counter': update_value}})
            fetched_rows = self.rrd.fetch('Average', start_time=self.start_time, end_time=(i + self.audit_freq))
            counters = [data['ds_counter'] for ts, data in fetched_rows]
            step = (i - self.start_time) / self.audit_freq
            # Test that we slide smoothly from the hires to the lower-res rra, and that the
            # values are sane.
            if step < 17:
                if step > 0:
                    self.assertEqual(round(step), round(counters[step - 1]))
            elif step == 17:
                fetched_rows = self.rrd.fetch('Average', start_time=self.start_time + 5 * self.audit_freq, end_time=i)
                counters = [data['ds_counter'] for ts, data in fetched_rows]
                self.assertNotIn(None, counters)
            elif step in range(21, 28):
                self.assertSequenceEqual([5.5, 15.5], counters)
            elif step in range(30, 38):
                self.assertSequenceEqual([5.5, 15.5, 25.5], counters)
            if step == 109:
                self.assertSequenceEqual([None, None, None, None, 45.5, 55.5, 65.5, 75.5, 85.5, 95.5, None], counters)

    def tearDown(self):
        self.rrd.delete()
