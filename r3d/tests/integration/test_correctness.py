## Copyright 2011 Whamcloud, Inc.
## Authors: Michael MacDonald <mjmac@whamcloud.com>

from django.test import TestCase
import r3d.models
from r3d.models import *
import json

class AverageRraTest(TestCase):
    """
    Tests each DS type with a high-resolution Average RRA and a
    low-resolution Average RRA.
    """
    def setUp(self):
        audit_freq = 60
        self.rrd = Database.objects.create(name="average_test",
                                           start=1318119548 - audit_freq,
                                           step=audit_freq)
        self.rrd.datasources.add(Counter.objects.create(name="counter",
                                                       heartbeat=audit_freq * 4,
                                                        database=self.rrd))
        self.rrd.datasources.add(Gauge.objects.create(name="gauge",
                                                       heartbeat=audit_freq * 4,
                                                        database=self.rrd))
        self.rrd.datasources.add(Derive.objects.create(name="derive",
                                                       heartbeat=audit_freq * 4,
                                                        database=self.rrd))
        self.rrd.datasources.add(Absolute.objects.create(name="absolute",
                                                       heartbeat=audit_freq * 4,
                                                        database=self.rrd))
        # Medium resolution, stores an hour's worth of 60s samples.
        # 3600 / 60 = 60 rows
        self.rrd.archives.add(Average.objects.create(xff="0.5",
                                                     cdp_per_row=1,
                                                     rows=3600 / audit_freq,
                                                     database=self.rrd))
        # Low resolution, stores a day's worth of 1hr samples.
        # 86400 / 3600 = 24 rows
        self.rrd.archives.add(Average.objects.create(xff="0.5",
                                                     cdp_per_row=3600 / audit_freq,
                                                     rows=24,
                                                     database=self.rrd))

    def update_database(self):
        import os, re

        datafile = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "sample_data", "avg_rra.txt"))
        for line in datafile.readlines():
            if re.match("^#", line):
                continue
            self.rrd.update(line[:-1])

    def load_xport(self, filename):
        from xml.dom.minidom import parse, parseString
        import os

        def get_row_time(row):
            return long(row.getElementsByTagName("t")[0].childNodes[0].data)

        def get_legend(xport):
            legend = []
            for entry in xport.getElementsByTagName("entry"):
                legend.append(entry.childNodes[0].data)
            return legend

        results = []
        xport = parse(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "..", "sample_data", filename))
        legend = get_legend(xport)
        for row in xport.getElementsByTagName("row"):
            row_dict = {}
            values = row.getElementsByTagName("v")
            for idx in range(0, len(values)):
                text = values[idx].childNodes[0].data
                row_dict[legend[idx]] = float(text) if text != "NaN" else None
            results.append((get_row_time(row), row_dict))

        return tuple(results)

    # Sigh.
    def massage_results(self, results):
        massaged = []
        for row in results:
            newrow = [row[0], row[1]]
            for k, v in row[1].items():
                newrow[1][k] = float("%0.10e" % v) if v else None
            massaged.append(tuple(newrow))

        return tuple(massaged)

    def test_database_fetch(self):
        """
        Tests that what we get back from fetch() is correct.
        """
        self.maxDiff = None
        self.update_database()

        expected = self.load_xport("avg_rra_step.xml")
        actual = self.rrd.fetch("Average", 1318149238, 1318149488)
        massaged = self.massage_results(actual)
        self.assertEqual(expected, massaged)

        expected = self.load_xport("avg_rra_full.xml")
        actual = self.rrd.fetch("Average", 1318119488, 1318149488)
        massaged = self.massage_results(actual)
        self.assertEqual(expected, massaged)

    def tearDown(self):
        self.rrd.delete()

class MinRraTest(TestCase):
    """
    Tests each DS type with a high-resolution Min RRA and a
    low-resolution Min RRA.
    """
    def setUp(self):
        audit_freq = 60
        self.rrd = Database.objects.create(name="min_test",
                                           start=1318119548 - audit_freq,
                                           step=audit_freq)
        self.rrd.datasources.add(Counter.objects.create(name="counter",
                                                       heartbeat=audit_freq * 4,
                                                        database=self.rrd))
        self.rrd.datasources.add(Gauge.objects.create(name="gauge",
                                                       heartbeat=audit_freq * 4,
                                                        database=self.rrd))
        self.rrd.datasources.add(Derive.objects.create(name="derive",
                                                       heartbeat=audit_freq * 4,
                                                        database=self.rrd))
        self.rrd.datasources.add(Absolute.objects.create(name="absolute",
                                                       heartbeat=audit_freq * 4,
                                                        database=self.rrd))
        # Medium resolution, stores an hour's worth of 60s samples.
        # 3600 / 60 = 60 rows
        self.rrd.archives.add(Min.objects.create(xff="0.5",
                                                 cdp_per_row=1,
                                                 rows=3600 / audit_freq,
                                                 database=self.rrd))
        # Low resolution, stores a day's worth of 1hr samples.
        # 86400 / 3600 = 24 rows
        self.rrd.archives.add(Min.objects.create(xff="0.5",
                                                 cdp_per_row=3600 / audit_freq,
                                                 rows=24,
                                                 database=self.rrd))

    def update_database(self):
        import os, re

        datafile = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "sample_data", "min_rra.txt"))
        for line in datafile.readlines():
            if re.match("^#", line):
                continue
            self.rrd.update(line[:-1])

    def load_xport(self, filename):
        from xml.dom.minidom import parse, parseString
        import os

        def get_row_time(row):
            return long(row.getElementsByTagName("t")[0].childNodes[0].data)

        def get_legend(xport):
            legend = []
            for entry in xport.getElementsByTagName("entry"):
                legend.append(entry.childNodes[0].data)
            return legend

        results = []
        xport = parse(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "..", "sample_data", filename))
        legend = get_legend(xport)
        for row in xport.getElementsByTagName("row"):
            row_dict = {}
            values = row.getElementsByTagName("v")
            for idx in range(0, len(values)):
                text = values[idx].childNodes[0].data
                row_dict[legend[idx]] = float(text) if text != "NaN" else None
            results.append((get_row_time(row), row_dict))

        return tuple(results)

    # Sigh.
    def massage_results(self, results):
        massaged = []
        for row in results:
            newrow = [row[0], row[1]]
            for k, v in row[1].items():
                newrow[1][k] = float("%0.10e" % v) if v else None
            massaged.append(tuple(newrow))

        return tuple(massaged)

    def test_database_fetch(self):
        """
        Tests that what we get back from fetch() is correct.
        """
        self.maxDiff = None
        self.update_database()

        expected = self.load_xport("min_rra_step.xml")
        actual = self.rrd.fetch("Min", 1318149238, 1318149488)
        massaged = self.massage_results(actual)
        self.assertEqual(expected, massaged)

        expected = self.load_xport("min_rra_full.xml")
        actual = self.rrd.fetch("Min", 1318119488, 1318149488)
        massaged = self.massage_results(actual)
        self.assertEqual(expected, massaged)

    def tearDown(self):
        self.rrd.delete()

class MaxRraTest(TestCase):
    """
    Tests each DS type with a high-resolution Max RRA and a
    low-resolution Max RRA.
    """
    def setUp(self):
        audit_freq = 60
        self.rrd = Database.objects.create(name="max_test",
                                           start=1318119548 - audit_freq,
                                           step=audit_freq)
        self.rrd.datasources.add(Counter.objects.create(name="counter",
                                                       heartbeat=audit_freq * 4,
                                                        database=self.rrd))
        self.rrd.datasources.add(Gauge.objects.create(name="gauge",
                                                       heartbeat=audit_freq * 4,
                                                        database=self.rrd))
        self.rrd.datasources.add(Derive.objects.create(name="derive",
                                                       heartbeat=audit_freq * 4,
                                                        database=self.rrd))
        self.rrd.datasources.add(Absolute.objects.create(name="absolute",
                                                       heartbeat=audit_freq * 4,
                                                        database=self.rrd))
        # Medium resolution, stores an hour's worth of 60s samples.
        # 3600 / 60 = 60 rows
        self.rrd.archives.add(Max.objects.create(xff="0.5",
                                                 cdp_per_row=1,
                                                 rows=3600 / audit_freq,
                                                 database=self.rrd))
        # Low resolution, stores a day's worth of 1hr samples.
        # 86400 / 3600 = 24 rows
        self.rrd.archives.add(Max.objects.create(xff="0.5",
                                                 cdp_per_row=3600 / audit_freq,
                                                 rows=24,
                                                 database=self.rrd))

    def update_database(self):
        import os, re

        datafile = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "sample_data", "max_rra.txt"))
        for line in datafile.readlines():
            if re.match("^#", line):
                continue
            self.rrd.update(line[:-1])

    def load_xport(self, filename):
        from xml.dom.minidom import parse, parseString
        import os

        def get_row_time(row):
            return long(row.getElementsByTagName("t")[0].childNodes[0].data)

        def get_legend(xport):
            legend = []
            for entry in xport.getElementsByTagName("entry"):
                legend.append(entry.childNodes[0].data)
            return legend

        results = []
        xport = parse(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "..", "sample_data", filename))
        legend = get_legend(xport)
        for row in xport.getElementsByTagName("row"):
            row_dict = {}
            values = row.getElementsByTagName("v")
            for idx in range(0, len(values)):
                text = values[idx].childNodes[0].data
                row_dict[legend[idx]] = float(text) if text != "NaN" else None
            results.append((get_row_time(row), row_dict))

        return tuple(results)

    # Sigh.
    def massage_results(self, results):
        massaged = []
        for row in results:
            newrow = [row[0], row[1]]
            for k, v in row[1].items():
                newrow[1][k] = float("%0.10e" % v) if v else None
            massaged.append(tuple(newrow))

        return tuple(massaged)

    def test_database_fetch(self):
        """
        Tests that what we get back from fetch() is correct.
        """
        self.maxDiff = None
        self.update_database()

        expected = self.load_xport("max_rra_step.xml")
        actual = self.rrd.fetch("Max", 1318149238, 1318149488)
        massaged = self.massage_results(actual)
        self.assertEqual(expected, massaged)

        expected = self.load_xport("max_rra_full.xml")
        actual = self.rrd.fetch("Max", 1318119488, 1318149488)
        massaged = self.massage_results(actual)
        self.assertEqual(expected, massaged)

    def tearDown(self):
        self.rrd.delete()

class LastRraTest(TestCase):
    """
    Tests each DS type with a high-resolution Last RRA and a
    low-resolution Last RRA.
    """
    def setUp(self):
        audit_freq = 60
        self.rrd = Database.objects.create(name="last_test",
                                           start=1318119548 - audit_freq,
                                           step=audit_freq)
        self.rrd.datasources.add(Counter.objects.create(name="counter",
                                                       heartbeat=audit_freq * 4,
                                                        database=self.rrd))
        self.rrd.datasources.add(Gauge.objects.create(name="gauge",
                                                       heartbeat=audit_freq * 4,
                                                        database=self.rrd))
        self.rrd.datasources.add(Derive.objects.create(name="derive",
                                                       heartbeat=audit_freq * 4,
                                                        database=self.rrd))
        self.rrd.datasources.add(Absolute.objects.create(name="absolute",
                                                       heartbeat=audit_freq * 4,
                                                        database=self.rrd))
        # Medium resolution, stores an hour's worth of 60s samples.
        # 3600 / 60 = 60 rows
        self.rrd.archives.add(Last.objects.create(xff="0.5",
                                                 cdp_per_row=1,
                                                 rows=3600 / audit_freq,
                                                 database=self.rrd))
        # Low resolution, stores a day's worth of 1hr samples.
        # 86400 / 3600 = 24 rows
        self.rrd.archives.add(Last.objects.create(xff="0.5",
                                                 cdp_per_row=3600 / audit_freq,
                                                 rows=24,
                                                 database=self.rrd))

    def update_database(self):
        import os, re

        datafile = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "sample_data", "last_rra.txt"))
        for line in datafile.readlines():
            if re.match("^#", line):
                continue
            self.rrd.update(line[:-1])

    def load_xport(self, filename):
        from xml.dom.minidom import parse, parseString
        import os

        def get_row_time(row):
            return long(row.getElementsByTagName("t")[0].childNodes[0].data)

        def get_legend(xport):
            legend = []
            for entry in xport.getElementsByTagName("entry"):
                legend.append(entry.childNodes[0].data)
            return legend

        results = []
        xport = parse(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "..", "sample_data", filename))
        legend = get_legend(xport)
        for row in xport.getElementsByTagName("row"):
            row_dict = {}
            values = row.getElementsByTagName("v")
            for idx in range(0, len(values)):
                text = values[idx].childNodes[0].data
                row_dict[legend[idx]] = float(text) if text != "NaN" else None
            results.append((get_row_time(row), row_dict))

        return tuple(results)

    # Sigh.
    def massage_results(self, results):
        massaged = []
        for row in results:
            newrow = [row[0], row[1]]
            for k, v in row[1].items():
                newrow[1][k] = float("%0.10e" % v) if v else None
            massaged.append(tuple(newrow))

        return tuple(massaged)

    def test_database_fetch(self):
        """
        Tests that what we get back from fetch() is correct.
        """
        self.LastDiff = None
        self.update_database()

        expected = self.load_xport("last_rra_step.xml")
        actual = self.rrd.fetch("Last", 1318149238, 1318149488)
        massaged = self.massage_results(actual)
        self.assertEqual(expected, massaged)

        expected = self.load_xport("last_rra_full.xml")
        actual = self.rrd.fetch("Last", 1318119488, 1318149488)
        massaged = self.massage_results(actual)
        self.assertEqual(expected, massaged)

    def tearDown(self):
        self.rrd.delete()

class DatabaseNamesShouldBeUnique(TestCase):
    """
    Database names should be unique.  While the primary mechanism
    for referencing R3D databases will be via the ContentTypes system,
    Database names should also be useful for access.
    """
    def test_double_create_raises_integrity_error(self):
        from django.contrib.auth.models import User
        from django.contrib.contenttypes.models import ContentType
        from django.db import IntegrityError

        audit_freq = 1

        user = User.objects.create(username='test', email='test@test.test')
        ct = ContentType.objects.get_for_model(user)

        self.rrd = Database.objects.create(name="uniq_test",
                                           start=1318119547,
                                           step=audit_freq)

        self.assertRaises(IntegrityError,
                          Database.objects.create,
                          name="uniq_test",
                          start=1318119547,
                          step=audit_freq)

    def tearDown(self):
        self.rrd.delete()

class SimpleFetchWithDateTimes(TestCase):
    """
    All of the other testcases use ints for start/end times.  Since we've
    added support for datetimes, we need to do some basic testing to
    make sure they work properly.
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

    def test_database_fetch_with_datetimes(self):
        """
        Tests that what we get back from fetch() with datetimes is correct.
        """
        self.maxDiff = None
        self.update_database()
        from datetime import datetime

        int_start = 920804400
        start_time = datetime.fromtimestamp(int_start)
        int_end = 920809200
        end_time = datetime.fromtimestamp(int_end)

        dt_fetch = self.rrd.fetch("Average", start_time, end_time)
        int_fetch = self.rrd.fetch("Average", int_start, int_end)
        self.assertEqual(dt_fetch, int_fetch)

        int_start = 920799000
        start_time = datetime.fromtimestamp(int_start)
        int_end = 920809200
        end_time = datetime.fromtimestamp(int_end)

        dt_fetch = self.rrd.fetch("Average", start_time, end_time)
        int_fetch = self.rrd.fetch("Average", int_start, int_end)
        self.assertEqual(dt_fetch, int_fetch)

    def tearDown(self):
        self.rrd.delete()
