import unittest
# FIXME: import TestCase from django.test
from test_base_layout import Layout
from test_alerts import TestAlerts
from test_events import TestEvents
from test_logs import TestLogs
from test_bread_crumb import TestBreadCrumb


def suite():
    ui_layout = unittest.TestLoader().loadTestsFromTestCase(Layout)

    test_Alerts = unittest.TestLoader().loadTestsFromTestCase(TestAlerts)
    test_Events = unittest.TestLoader().loadTestsFromTestCase(TestEvents)
    test_Logs = unittest.TestLoader().loadTestsFromTestCase(TestLogs)

    test_Breadcrumb = unittest.TestLoader().loadTestsFromTestCase(TestBreadCrumb)

    alltests = unittest.TestSuite([
                            ui_layout,
                            test_Alerts,
                            test_Events,
                            test_Logs,
                            test_Breadcrumb,
                            ])
    return alltests

if __name__ == "__main__":
    runner = unittest.TextTestRunner()
    test_suite = suite()
    runner.run(test_suite)
