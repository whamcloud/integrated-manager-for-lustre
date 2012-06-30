import unittest
# FIXME: import TestCase from django.test
from test_base_layout import TestBaseLayout
from test_events import TestEvents
from test_logs import TestLogs
from test_servers import TestServer
from test_mgt import TestMgt
from test_bread_crumb import TestBreadCrumb
from test_create_filesystem import TestCreateFilesystem
from test_filesystem import TestFilesystem
from test_edit_filesystem import TestEditFilesystem


def suite():
    ui_layout = unittest.TestLoader().loadTestsFromTestCase(TestBaseLayout)

    test_Events = unittest.TestLoader().loadTestsFromTestCase(TestEvents)
    test_Logs = unittest.TestLoader().loadTestsFromTestCase(TestLogs)

    test_Breadcrumb = unittest.TestLoader().loadTestsFromTestCase(TestBreadCrumb)

    test_server = unittest.TestLoader().loadTestsFromTestCase(TestServer)
    test_mgt = unittest.TestLoader().loadTestsFromTestCase(TestMgt)

    test_create_filesystem = unittest.TestLoader().loadTestsFromTestCase(TestCreateFilesystem)
    test_filesystem = unittest.TestLoader().loadTestsFromTestCase(TestFilesystem)
    test_edit_filesystem = unittest.TestLoader().loadTestsFromTestCase(TestEditFilesystem)

    alltests = unittest.TestSuite([
                            ui_layout,
                            test_Events,
                            test_Logs,
                            test_Breadcrumb,
                            test_server,
                            test_mgt,
                            test_create_filesystem,
                            test_filesystem,
                            test_edit_filesystem
                            ])
    return alltests

if __name__ == "__main__":
    runner = unittest.TextTestRunner()
    test_suite = suite()
    runner.run(test_suite)
