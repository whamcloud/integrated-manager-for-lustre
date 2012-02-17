import unittest
# FIXME: import TestCase from django.test
from test_base_layout import Layout
from test_alerts import TestAlerts
from test_events import TestEvents
from test_logs import TestLogs
from test_mgt import TestMgt
from test_create_filesystem import CreateFileSystem


def suite():
    ui_layout = unittest.TestLoader().loadTestsFromTestCase(Layout)

    test_Alerts = unittest.TestLoader().loadTestsFromTestCase(TestAlerts)
    test_Events = unittest.TestLoader().loadTestsFromTestCase(TestEvents)
    test_Logs = unittest.TestLoader().loadTestsFromTestCase(TestLogs)

    test_Mgt = unittest.TestLoader().loadTestFromTestCase(TestMgt)
    test_create_filesystem = unittest.TestLoader().loadTestsFromTestCase(CreateFileSystem)

    alltests = unittest.TestSuite([
                            ui_layout,
                            test_Alerts,
                            test_Events,
                            test_Logs,
                            test_Mgt,
                            test_create_filesystem
                            ])
    return alltests

if __name__ == "__main__":
    runner = unittest.TextTestRunner()
    test_suite = suite()
    runner.run(test_suite)
