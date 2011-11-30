## Copyright 2011 Whamcloud, Inc.
## Authors: Michael MacDonald <mjmac@whamcloud.com>

from django.test import TestCase
import math
import fudge
from r3d import lib
import r3d.models

class DataSourceTestCase(TestCase):
    @fudge.patch('r3d.models.Datasource.database')
    def setUp(self, fake_database):
        test_class = getattr(r3d.models,
                             self.__class__.__name__.replace("Test",""))
        ds = test_class()
        ds.name = "speed"
        ds.heartbeat = 600
        ds.last_reading = 12345
        ds.pdp_scratch = 0
        ds.new_reading = 12357
        ds.unknown_seconds = 0

        ds.database = fudge.Fake('Database')
        (ds.database.has_attr(step=300)
                    .has_attr(last_update=920804700)
        )
        self.ds = ds

        self.update_time = 920805000
        self.interval = float(self.update_time) - float(ds.database.last_update)

class TestAbsolute(DataSourceTestCase):
    pass

class TestCounter(DataSourceTestCase):
    __test__ = False

    @fudge.patch('r3d.models.Datasource.database')
    def test_first_update_pdp_temp(self, fake_database):
        self.ds.last_reading = lib.DNAN
        self.ds.update_pdp_temp(self.update_time, self.interval)
        self.assertTrue(math.isnan(self.ds.pdp_temp))

    @fudge.patch('r3d.models.Datasource.database')
    def test_second_update_pdp_temp(self, fake_database):
        self.ds.update_pdp_temp(self.update_time, self.interval)
        self.assertEqual(self.ds.pdp_temp, 12)

class TestDerive(DataSourceTestCase):
    pass

class TestGauge(DataSourceTestCase):
    pass
