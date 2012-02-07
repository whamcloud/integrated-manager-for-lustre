import unittest
# FIXME: import TestCase from django.test
from test_base_layout import Layout
from test_alerts import Alertsdata
from test_events import Eventsdata
from test_logs import Logsdata
from test_create_filesystem import CreateFileSystem


def suite():
    ui_layout = unittest.TestLoader().loadTestsFromTestCase(Layout)
    test_alerts_data = unittest.TestLoader().loadTestsFromTestCase(Alertsdata)
    test_events_data = unittest.TestLoader().loadTestsFromTestCase(Eventsdata)
    test_logs_data = unittest.TestLoader().loadTestsFromTestCase(Logsdata)
    test_create_filesystem = unittest.TestLoader().loadTestsFromTestCase(CreateFileSystem)

    alltests = unittest.TestSuite([
                            ui_layout,
                            test_alerts_data,
                            test_events_data,
                            test_logs_data,
                            test_create_filesystem
                            ])
    return alltests

if __name__ == "__main__":
    runner = unittest.TextTestRunner()
    test_suite = suite()
    runner.run(test_suite)
