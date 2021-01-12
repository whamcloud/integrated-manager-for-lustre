import datetime
import mock
import unittest

from emf_common.lib.date_time import EMFDateTime
from emf_common.lib.date_time import FixedOffset
from emf_common.lib.date_time import LocalOffset


class TestEMFDateTime(unittest.TestCase):
    def test_prase(self):
        for str, date_time in [
            (
                "2016/10/09T19:20:21+1000",
                EMFDateTime(
                    year=2016, month=10, day=9, hour=19, minute=20, second=21, microsecond=0, tzinfo=FixedOffset(600)
                ),
            ),
            (
                "2016/10/09T19:20:21.12345+1000",
                EMFDateTime(
                    year=2016,
                    month=10,
                    day=9,
                    hour=19,
                    minute=20,
                    second=21,
                    microsecond=123450,
                    tzinfo=FixedOffset(600),
                ),
            ),
            (
                "2016-10-09 19:20:21-1000",
                EMFDateTime(
                    year=2016, month=10, day=9, hour=19, minute=20, second=21, microsecond=0, tzinfo=FixedOffset(-600)
                ),
            ),
            (
                "2016-10-09 19:20:21.12345-1000",
                EMFDateTime(
                    year=2016,
                    month=10,
                    day=9,
                    hour=19,
                    minute=20,
                    second=21,
                    microsecond=123450,
                    tzinfo=FixedOffset(-600),
                ),
            ),
            (
                "19:20:21-1000 2016-10/09",
                EMFDateTime(
                    year=2016, month=10, day=9, hour=19, minute=20, second=21, microsecond=0, tzinfo=FixedOffset(-600)
                ),
            ),
            (
                "19:20:21.12345-0000 2016/10-09",
                EMFDateTime(
                    year=2016, month=10, day=9, hour=19, minute=20, second=21, microsecond=123450, tzinfo=FixedOffset(0)
                ),
            ),
            (
                "        19:20:21.12345        -1000              2016/10-09        ",
                EMFDateTime(
                    year=2016,
                    month=10,
                    day=9,
                    hour=19,
                    minute=20,
                    second=21,
                    microsecond=123450,
                    tzinfo=FixedOffset(-600),
                ),
            ),
            ("2016/10-09", EMFDateTime(year=2016, month=10, day=9, tzinfo=FixedOffset(0))),
            (
                "19:20:21.12345-0000",
                EMFDateTime(
                    year=1900, month=1, day=1, hour=19, minute=20, second=21, microsecond=123450, tzinfo=FixedOffset(0)
                ),
            ),
            (
                "19:20:21-0500",
                EMFDateTime(
                    year=1900, month=1, day=1, hour=19, minute=20, second=21, microsecond=0, tzinfo=FixedOffset(-300)
                ),
            ),
        ]:
            self.assertEqual(EMFDateTime.parse(str), date_time)


class TestFixedOffset(unittest.TestCase):
    def test_properties_negative(self):
        fixed_offset = FixedOffset(-300)

        self.assertEqual(fixed_offset.offset, datetime.timedelta(days=-1, hours=19))
        self.assertEqual(fixed_offset.utcoffset(), datetime.timedelta(days=-1, hours=19))
        self.assertEqual(fixed_offset.tzname(), "<-1 day, 19:00:00>")
        self.assertEqual(fixed_offset.dst(), datetime.timedelta(seconds=0))
        self.assertEqual(str(fixed_offset), "-0500")

    def test_properties_positive(self):
        fixed_offset = FixedOffset(567)

        self.assertEqual(fixed_offset.offset, datetime.timedelta(hours=9, minutes=27))
        self.assertEqual(fixed_offset.utcoffset(), datetime.timedelta(hours=9, minutes=27))
        self.assertEqual(fixed_offset.tzname(), "<9:27:00>")
        self.assertEqual(fixed_offset.dst(), datetime.timedelta(seconds=0))
        self.assertEqual(str(fixed_offset), "0927")


class TestLocalOffset(unittest.TestCase):
    class MockDateTime(datetime.datetime):
        now_time = None
        utc_time = None

        @classmethod
        def now(cls, tz=None):
            return cls.now_time

        @classmethod
        def utcnow(cls):
            return cls.utc_time

    def setUp(self):
        self.MockDateTime.utc_time = datetime.datetime(year=2010, month=4, day=20, hour=20, minute=13, second=2)
        self.MockDateTime.now_time = datetime.datetime(year=2010, month=4, day=20, hour=21, minute=13, second=2)

        mock.patch("emf_common.lib.date_time.datetime", self.MockDateTime).start()

    def test_properties_gmt(self):
        local_offset = LocalOffset()

        self.assertEqual(local_offset.offset, datetime.timedelta(hours=1, minutes=0))
        self.assertEqual(local_offset.utcoffset(), datetime.timedelta(hours=1, minutes=0))
        self.assertEqual(local_offset.tzname(), "<1:00:00>")
        self.assertEqual(local_offset.dst(), datetime.timedelta(seconds=0))
        self.assertEqual(str(local_offset), "0100")

    def test_properties_cst(self):
        self.MockDateTime.now_time = datetime.datetime(year=2010, month=4, day=20, hour=13, minute=13, second=2)

        local_offset = LocalOffset()

        self.assertEqual(local_offset.offset, datetime.timedelta(days=-1, hours=17, minutes=0))
        self.assertEqual(local_offset.utcoffset(), datetime.timedelta(days=-1, hours=17, minutes=0))
        self.assertEqual(local_offset.tzname(), "<-1 day, 17:00:00>")
        self.assertEqual(local_offset.dst(), datetime.timedelta(seconds=0))
        self.assertEqual(str(local_offset), "-0700")

    def test_properties_ist(self):
        self.MockDateTime.now_time = datetime.datetime(year=2010, month=4, day=21, hour=1, minute=43, second=2)

        local_offset = LocalOffset()

        self.assertEqual(local_offset.offset, datetime.timedelta(hours=5, minutes=30))
        self.assertEqual(local_offset.utcoffset(), datetime.timedelta(hours=5, minutes=30))
        self.assertEqual(local_offset.tzname(), "<5:30:00>")
        self.assertEqual(local_offset.dst(), datetime.timedelta(seconds=0))
        self.assertEqual(str(local_offset), "0530")
