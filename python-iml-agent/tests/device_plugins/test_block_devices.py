import json
import os

import unittest
from mock import patch


class TestBase(unittest.TestCase):
    test_host_fqdn = "vm5.foo.com"

    def setUp(self):
        super(TestBase, self).setUp()
        self.test_root = os.path.join(os.path.dirname(__file__), "..", "data", "device_plugins")
        self.addCleanup(patch.stopall)

    def load(self, filename):
        return open(os.path.join(self.test_root, filename)).read()

    def check(self, skip_keys, expect, result, x):
        from toolz import pipe
        from toolz.curried import map as cmap, filter as cfilter

        def cmpval(key):
            expected = expect[x][key]
            actual = result[x][key]
            if type(expected) is dict:
                self.check(skip_keys, expect[x], result[x], key)
            else:
                self.assertEqual(
                    actual,
                    expected,
                    "item {} ({}) in {} does not match expected ({})".format(key, actual, x, expected),
                )

        pipe(expect[x].keys(), cfilter(lambda y: y not in skip_keys), cmap(cmpval), list)
