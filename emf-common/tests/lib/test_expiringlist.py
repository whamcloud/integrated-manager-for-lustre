from mock import patch
from emf_common.lib.util import ExpiringList
from emf_common.test.emf_unit_testcase import EmfUnitTestCase


class TestExpiringList(EmfUnitTestCase):
    def setUp(self):
        super(TestExpiringList, self).setUp()
        self.exping_list = ExpiringList(10)
        patcher_time = patch("time.time")
        self.addCleanup(patcher_time.stop)
        self.mock_time = patcher_time.start()
        self.mock_time.return_value = 0

    def test_not_expired(self):
        self.exping_list.append("value")
        self.assertIn("value", self.exping_list)
        self.assertEqual(1, len(self.exping_list))
        self.assertEqual("value", self.exping_list[0])

    def test_expired(self):
        self.exping_list.append("value")
        self.mock_time.return_value = 60 * 10 + 1
        self.assertNotIn("value", self.exping_list)
        self.assertEqual(0, len(self.exping_list))

    def test_deletion(self):
        self.exping_list.append("value 1")
        self.exping_list.append("value 2")
        del self.exping_list[0]
        self.assertEqual(1, len(self.exping_list))
        self.assertEqual("value 2", self.exping_list[0])

    def test_stringify(self):
        self.exping_list.append("value")
        self.assertEqual("['value']", str(self.exping_list))

    def test_multiple_entries(self):
        map(self.exping_list.append, range(1, 101))
        self.assertEqual(100, len(self.exping_list))
        self.mock_time.return_value = 30
        map(self.exping_list.append, range(101, 201))
        self.assertEqual(100, len(self.exping_list))
        self.mock_time.return_value = 60
        self.exping_list.append("value")
        self.assertIn("value", self.exping_list)
        self.assertEqual(1, len(self.exping_list))
        self.assertEqual("value", self.exping_list[0])
