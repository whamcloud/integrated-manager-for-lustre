# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import re
from datetime import datetime
from datetime import tzinfo
from datetime import timedelta


class IMLDateTime(datetime):
    @classmethod
    def convert_datetime_to_utc(cls, tm_datetime_local):
        """Convert the local datetime to utc """

        utc_offset_timedelta = cls.now() - cls.utcnow()

        return tm_datetime_local - utc_offset_timedelta

    @classmethod
    def parse(cls, raw_date_str):
        date_match = re.match('.*(\d\d\d\d[-/]\d\d[-/]\d\d)', raw_date_str)
        time_match = re.match('.*(\d\d:\d\d:\d\d)', raw_date_str)
        microsecond_match = re.match('.*\.(\d*)', raw_date_str)
        zone_match = re.match('.*([+-]\d\d:?\d\d)', raw_date_str)

        microseconds = microsecond_match.group(1) if microsecond_match else '0'

        if date_match and time_match:
            naive_date_str = "%s %s.%s" % (date_match.group(1).replace('/', '-'),
                                           time_match.group(1),
                                           microseconds)

            naive_dt = IMLDateTime.strptime(naive_date_str, '%Y-%m-%d %H:%M:%S.%f')
        elif date_match:
            naive_dt = IMLDateTime.strptime(date_match.group(1).replace('/', '-'), '%Y-%m-%d')
        elif time_match:
            naive_time_str = "%s.%s" % (time_match.group(1),
                                        microseconds)

            naive_dt = IMLDateTime.strptime(naive_time_str, '%H:%M:%S.%f')
        else:
            raise ValueError('Unable to parse "%s"' % raw_date_str)

        if zone_match:
            offset_str = zone_match.group(1).replace(':', '')

            offset = int(offset_str[-4:-2]) * 60 + int(offset_str[-2:])

            if offset_str[0] == "-":
                offset = -offset
        else:
            offset = 0

        return naive_dt.replace(tzinfo=FixedOffset(offset))

    @classmethod
    def utcnow(cls):
        return super(IMLDateTime, cls).utcnow().replace(tzinfo=FixedOffset(0))

    @classmethod
    def now(cls, tz=None):
        if tz is None:
            tz = LocalOffset()

        return super(IMLDateTime, cls).now(tz=tz)

    @property
    def as_datetime(self):
        """
        django seems to require an actual datetime - can you believe it rather than a instance of a child. Do they not
        understand inheritance! So return a datetime of the IMLDateTime
        :return: datetime
        """
        return datetime(year=self.year,
                        month=self.month,
                        day=self.day,
                        hour=self.hour,
                        minute=self.minute,
                        second=self.second,
                        microsecond=self.microsecond,
                        tzinfo=self.tzinfo)


class FixedOffset(tzinfo):
    """Fixed offset in minutes: `time = utc_time + utc_offset`."""
    def __init__(self, offset=0):
        self.offset = timedelta(minutes=offset)

    @property
    def offset(self):
        return self._offset

    @offset.setter
    def offset(self, offset_value):
        self._offset = offset_value

    def utcoffset(self, dt=None):
        return self._offset

    def tzname(self, dt=None):
        return '<%s>' % self._offset

    def dst(self, dt=None):
        return timedelta(0)

    def __repr__(self):
        minutes = int(self.offset.days * (60 * 24))
        minutes += int(self.offset.seconds / 60)
        minutes += int(self.offset.microseconds / (10 ^ 6)) / 60

        return '%s%02d%02d' % ('-' if minutes < 0 else '',
                               divmod(abs(minutes), 60)[0],
                               divmod(abs(minutes), 60)[1])


class LocalOffset(FixedOffset):
    """Fixed offset to localtime zone. `time = utc_time + local_offset`."""
    def __init__(self):
        utc_offset_timedelta = datetime.now() - datetime.utcnow()

        # because we can't stop time, we will find that the seconds are probably one less and microseconds is not
        # zero. We will have a difference that is something like. 0:59:59.999975
        if utc_offset_timedelta.microseconds != 0:
            utc_offset_timedelta = timedelta(days=utc_offset_timedelta.days,
                                             seconds=utc_offset_timedelta.seconds + 1,
                                             microseconds=0)

        utc_offset_timedelta_minutes = (utc_offset_timedelta.seconds + (utc_offset_timedelta.days * 24 * 3600)) / 60

        super(LocalOffset, self).__init__(utc_offset_timedelta_minutes)
