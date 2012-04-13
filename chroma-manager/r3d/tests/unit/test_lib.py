#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import time
import fudge
import math
from django.test import TestCase
from r3d.exceptions import BadUpdateString
from r3d.lib import parse_update_string, parse_update_time, parse_ds_vals, calculate_elapsed_steps


class TestParseUpdateString(TestCase):
    # slightly DRY-er, but not great
    def dry_fput(self, stub):
        self.now = int(time.time())
        (stub.expects_call()
             .with_args('N')
             .returns(self.now))

    def test_invalid_update_strings(self):
        self.assertRaises(BadUpdateString, parse_update_string, "")
        self.assertRaises(BadUpdateString, parse_update_string, "@Oct 12:1:2")
        self.assertRaises(BadUpdateString, parse_update_string, ":2")


class TestParseDsVals(TestCase):
    def test_valid_string_single_ds(self):
        values = parse_ds_vals("12345")
        self.assertEquals(values[0], 12345)
        self.assertEquals(len(values), 1)

    def test_valid_string_multi_ds(self):
        values = parse_ds_vals("12345:678:9012:3456789.01")
        self.assertEquals(values[0], 12345)
        self.assertEquals(values[-1], 3456789.01)
        self.assertEquals(len(values), 4)

    def test_valid_string_unknown_vals(self):
        values = parse_ds_vals("U::9012:3456789.01")
        self.assertTrue(math.isnan(values[0]))
        self.assertTrue(math.isnan(values[1]))
        self.assertEquals(values[-1], 3456789.01)
        self.assertEquals(len(values), 4)

    def test_invalid_string(self):
        self.assertRaises(BadUpdateString, parse_ds_vals, "x:y:2")


class TestParseTimeString(TestCase):
    @fudge.patch('time.time')
    def test_valid_N_string(self, fake_time):
        (fake_time.expects_call()
                  .returns(123456789))
        self.now = int(time.time())
        self.assertEquals(parse_update_time("N"), self.now)

    def test_valid_int_string(self):
        int_string = "123456"
        int_time = 123456
        self.assertEquals(parse_update_time(int_string), int_time)

    def test_valid_int(self):
        int_time = 123456
        self.assertEquals(parse_update_time(int_time), int_time)

    def test_valid_float_string(self):
        float_string = "123456.789"
        int_time = 123456
        self.assertEquals(parse_update_time(float_string), int_time)

    def test_valid_float(self):
        float_time = 123456.789
        int_time = 123456
        self.assertEquals(parse_update_time(float_time), int_time)


class TestCalculateElapsedSteps(TestCase):
    def test_one_exact_step(self):
        last_update = 920805600
        step_length = 300
        update_time = 920805900
        interval = float(update_time) - float(last_update)

        (elapsed_steps,
         pre_int,
         post_int,
         pdp_count) = calculate_elapsed_steps(last_update,
                                              step_length,
                                              update_time,
                                              interval)
        self.assertEquals(elapsed_steps, 1)
        self.assertEquals(pre_int, 300)
        self.assertEquals(post_int, 0)
        #self.assertEquals(pdp_count, 3069352)
