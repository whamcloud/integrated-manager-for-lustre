## Copyright 2011 Whamcloud, Inc.
## Authors: Michael MacDonald <mjmac@whamcloud.com>

import time
import datetime
from django.test import TestCase
from r3d.models import Database


class TestDatabaseTimes(TestCase):
    def setUp(self):
        self.rrds = []

    def test_parse_time_int(self):
        rrd = Database(name="testparse")

        in_time = int(time.time())
        out_time = rrd._parse_time(in_time)

        self.assertEqual(in_time, out_time)

    def test_parse_time_float(self):
        rrd = Database(name="testparse")

        in_time = time.time()
        out_time = rrd._parse_time(in_time)

        self.assertEqual(int(in_time), out_time)

    def test_parse_time_string(self):
        rrd = Database(name="testparse")

        in_time = "%lf" % time.time()
        out_time = rrd._parse_time(in_time)

        self.assertEqual(int(float(in_time)), out_time)

    def test_parse_time_datetime(self):
        rrd = Database(name="testparse")

        in_datetime = datetime.datetime.now()
        out_time = rrd._parse_time(in_datetime)

        self.assertEqual(int(in_datetime.strftime("%s")), out_time)

    def test_start_time_int(self):
        start_time = int(time.time())
        self.rrds.append(Database.objects.create(name="test_start_int",
                                                 start=start_time))

        self.assertEqual(start_time, self.rrds[-1].start)

    def test_start_time_datetime(self):
        start_time = datetime.datetime.now()
        self.rrds.append(Database.objects.create(name="test_start_datetime",
                                                 start=start_time))

        int_start = int(start_time.strftime("%s"))
        self.assertEqual(int_start, self.rrds[-1].start)

    def tearDown(self):
        for rrd in self.rrds:
            rrd.delete()
