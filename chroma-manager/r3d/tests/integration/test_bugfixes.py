#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


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
            (1318119598L, {u'ds_counter': None, u'ds_gauge': None}),
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
        self.rrd.delete()
